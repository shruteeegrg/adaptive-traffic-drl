"""Training jobs: train a DQN for one client's traffic, in the background, with progress and cancel.

The recipe is the one the shipped agents were made with (configs/dqn_v_dqfd.yaml: learning from the density
rule's demonstrations kept in a frozen buffer, with a margin loss), because plain DQN training was unstable
and lost to the rule. Training is seed-dependent (some seeds tie the rule, some are a few percent worse), so a
job trains several seeds and keeps the best one, picked on SELECTION seeds (20000+). The advisor's test seeds
(30000+) are never used here, so the final evaluation of the chosen agent is still an honest exam.

A job is a folder:
    scenario.yaml / scenario.rou.xml   snapshot of the traffic it was trained on
    status.json                        live progress (rewritten atomically every episode)
    result.json                        written at the end: per-seed scores, the chosen seed, reference scores
    model.npz                          the chosen agent (only if the job finished)
    seed_<n>_best.npz, seed_<n>.csv    each seed's best checkpoint and training log
    job.log, cancel                    the process output; an empty file whose presence asks the job to stop

`start_job` launches `traffic-drl train-job` as a separate process so a web page can poll `read_status`.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from traffic_drl.agent import DQNAgent, evaluate, maybe_pretrain, train_agent
from traffic_drl.config import load_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "configs/dqn_v_dqfd.yaml"
RANKING_SEED_BASE = 20_000          # selection seeds for choosing between trained seeds (same as the sweep)
DEFAULT_EPISODES, DEFAULT_SEEDS = 120, (0, 1, 2)
STALE_AFTER = 180                   # seconds without a status update before a running job is called stalled


# Measured on this machine (30-minute episodes, 5 s decisions): each seed first spends a fixed time on the
# demonstrations, evaluations and scoring, then a roughly constant time per training episode.
SECONDS_PER_EPISODE, SECONDS_PER_SEED_FIXED = 2.5, 65.0


def estimate_minutes(episodes: int, n_seeds: int) -> float:
    """A rough wall-clock estimate for the job, shown before the client starts it."""
    return n_seeds * (episodes * SECONDS_PER_EPISODE + SECONDS_PER_SEED_FIXED) / 60.0


def workspace() -> Path:
    """Where client jobs live: $TRAFFIC_DRL_HOME, or <repo>/projects (git-ignored)."""
    return Path(os.environ.get("TRAFFIC_DRL_HOME") or ROOT / "projects")


class Status:
    """status.json for a job, rewritten atomically so a reader never sees half a file."""

    def __init__(self, out_dir: str, **initial):
        self.path = Path(out_dir) / "status.json"
        self.data = {"state": "queued", "stage": "", "message": "", "seed_index": 0, "seeds": [], "episode": 0,
                     "episodes": 0, "rewards": [], "evals": [], "started": time.time(), **initial}

    def update(self, **fields) -> None:
        self.data.update(fields, updated=time.time())
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        os.replace(tmp, self.path)


def read_status(out_dir: str) -> dict:
    """The job's current status, or {"state": "missing"}. A 'running' job that has not reported for a while is
    reported as 'stalled' (its process probably died)."""
    path = Path(out_dir) / "status.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"state": "missing"}
    if data.get("state") == "running" and time.time() - data.get("updated", 0) > STALE_AFTER:
        data = {**data, "state": "stalled"}
    return data


def request_cancel(out_dir: str) -> None:
    (Path(out_dir) / "cancel").touch()


def snapshot_scenario(scenario_yaml: str, out_dir: str) -> str:
    """Copy a scenario (yaml + route file) into the job folder so the job is self-contained and reproducible."""
    from traffic_drl.config import load_scenario

    sc = load_scenario(scenario_yaml)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(sc["route_file"], out / "scenario.rou.xml")
    (out / "scenario.yaml").write_text(
        f"name: {sc.get('name', 'scenario')}\ndescription: {json.dumps(str(sc.get('description', '')))}\n"
        "route_file: scenario.rou.xml\n")
    return str(out / "scenario.yaml")


def _reference_scores(env, config: dict, episodes: int) -> dict:
    """Fixed timer and density rule on the same selection seeds, so the client can see what the agent is up against."""
    from traffic_drl import compare

    out = {}
    for label, kind, arg in (("fixed", "fixed", "40"), ("rule", "actuated", "min=10,max=40,ratio=4,gap=0")):
        agent = compare.build_agent(kind, arg, config, env)
        runs = []
        for _ in range(episodes):
            if hasattr(agent, "reset"):
                agent.reset()
            runs.append(evaluate(env, agent, episodes=1, seed_base=RANKING_SEED_BASE)["mean_total_waiting"])
        out[label] = sum(runs) / len(runs)
    return out


def run_job(scenario_yaml: str, out_dir: str, config_path: str = DEFAULT_CONFIG, episodes: int = DEFAULT_EPISODES,
            seeds=DEFAULT_SEEDS, final_eval_episodes: int = 5, env_factory=None, log=print) -> dict:
    """Train one agent per seed on `scenario_yaml`, keep the best on the selection seeds, write the job folder.
    Returns result.json's content; on cancel or failure the status says so and no model is written."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    status = Status(str(out), state="running", stage="starting", episodes=episodes, seeds=list(seeds))
    status.update()
    config = load_config(config_path)
    dqn = config.get("dqn", {})
    eval_every, eval_episodes = dqn.get("eval_every"), dqn.get("eval_episodes", 2)
    if env_factory is None:
        from traffic_drl.env import TraciEnv

        env_factory = lambda: TraciEnv(config_path, scenario=scenario_yaml)   # noqa: E731
    env = env_factory()
    cancelled = lambda: (out / "cancel").exists()   # noqa: E731
    rows = []
    try:
        for si, seed in enumerate(seeds):
            cfg = copy.deepcopy(config)
            cfg.setdefault("dqn", {})["seed"] = int(seed)
            agent = DQNAgent.from_config(cfg, state_dim=env.state_size)
            status.update(seed_index=si, stage="learning from the density rule's demonstrations", episode=0, rewards=[],
                          message=f"seed {seed} ({si + 1} of {len(seeds)})")
            if cancelled():
                break
            pretrained = maybe_pretrain(env, agent, cfg)
            status.update(stage="training")

            def on_episode(info, si=si, seed=seed):
                status.data["rewards"].append(round(info["reward"], 2))
                if info["eval"] is not None:
                    status.data["evals"].append({"seed": seed, "episode": info["episode"],
                                                 "waiting": round(info["eval"]["mean_total_waiting"], 2)})
                status.update(episode=info["episode"], seed_index=si)
                return cancelled()

            best = str(out / f"seed_{seed}_best.npz")
            history = {}
            train_agent(env, agent, episodes, max_steps=dqn.get("max_steps"), verbose=False, eval_at_start=pretrained,
                        log_path=str(out / f"seed_{seed}.csv"), eval_every=eval_every, eval_episodes=eval_episodes,
                        best_path=best, history=history, on_episode=on_episode)
            if cancelled():
                break
            status.update(stage="scoring this seed on selection seeds")
            if history.get("best_episode") is not None and os.path.exists(best):
                agent.load(best)
            else:
                agent.save(best)
            final = evaluate(env, agent, final_eval_episodes, max_steps=dqn.get("max_steps"), seed_base=RANKING_SEED_BASE)
            rows.append({"seed": int(seed), "best_episode": history.get("best_episode"), "file": best, **final})
            log(f"seed {seed}: waiting {final['mean_total_waiting']:.1f} on selection seeds")
        if cancelled() or not rows:
            status.update(state="cancelled", stage="", message="Stopped before a model was chosen.")
            return {}
        status.update(stage="comparing with the fixed timer and the density rule")
        reference = _reference_scores(env, config, final_eval_episodes)
        chosen = min(rows, key=lambda r: r["mean_total_waiting"])
        shutil.copy(chosen["file"], out / "model.npz")
        result = {"scenario": str(out / "scenario.yaml"), "config": config_path, "episodes": episodes,
                  "seeds": rows, "chosen_seed": chosen["seed"], "model": str(out / "model.npz"),
                  "selection_waiting": chosen["mean_total_waiting"], "reference_waiting": reference,
                  "note": "Scores are on selection seeds (20000+), used to choose the seed. They are not a test result: "
                          "evaluate on fresh seeds (traffic-drl advise) before relying on this agent."}
        (out / "result.json").write_text(json.dumps(result, indent=2))
        status.update(state="done", stage="", message="Training finished.")
        return result
    except Exception as e:   # the job runs unattended: record why it failed instead of dying silently
        status.update(state="failed", stage="", message=f"{type(e).__name__}: {e}")
        raise
    finally:
        env.close()


def start_job(scenario_yaml: str, name: str = "job", episodes: int = DEFAULT_EPISODES, seeds=DEFAULT_SEEDS,
              config_path: str = DEFAULT_CONFIG, base_dir: str = None) -> tuple:
    """Snapshot the scenario into a fresh job folder and launch `traffic-drl train-job` in the background.
    Returns (job_dir, Popen). The folder already holds a 'queued' status so the first poll finds something."""
    base = Path(base_dir) if base_dir else workspace() / "jobs"
    job_dir = base / f"{''.join(c for c in name if c.isalnum() or c in '_-') or 'job'}_{time.strftime('%Y%m%d_%H%M%S')}"
    snapshot = snapshot_scenario(scenario_yaml, str(job_dir))
    Status(str(job_dir), state="queued", episodes=episodes, seeds=list(seeds)).update()
    cmd = [sys.executable, "-m", "traffic_drl.cli", "train-job", "--scenario", snapshot, "--out-dir", str(job_dir),
           "--config", str(ROOT / config_path) if not os.path.isabs(config_path) else config_path,
           "--episodes", str(episodes), "--seeds", ",".join(str(s) for s in seeds)]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=open(job_dir / "job.log", "w"), stderr=subprocess.STDOUT,
                            start_new_session=True)
    return str(job_dir), proc
