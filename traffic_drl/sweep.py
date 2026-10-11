"""Hyperparameter sweep for the DQN agent (Week 6).

Trains every combination of the grid x every seed on one scenario, scores
each trained agent with a greedy evaluation on unseen SUMO seeds, and
writes:
  sweep_runs.csv      one row per (setting, seed)
  sweep_summary.csv   one row per setting: mean/std over seeds, ranked
  runs/<id>_best.npz  best-so-far checkpoint of each run
  runs/<id>.csv       each run's training log (reward curve + metrics)
  runs/<id>_evals.csv each run's periodic greedy evaluations
Ranking uses mean_total_waiting (average halted vehicles plus vehicles
stuck waiting to enter the network, lower is better): total delay at fixed
demand per simulated second, valid even when demand overloads the junction.
The other metrics are reported alongside. Where the env has no metrics (the toy
model), reward is used instead.
"""

import copy
import csv
import itertools
import json
import os
import statistics

from traffic_drl.agent import DQNAgent, evaluate, train_agent

METRIC_KEYS = ("reward", "mean_total_waiting", "mean_queue", "mean_backlog",
               "avg_wait_per_vehicle", "throughput_per_hour", "switches", "ns_green_fraction")


REWARD_PREFIX = "reward."   # grid keys like "reward.switch_penalty" tune the env's reward, not the agent


def expand_grid(grid: dict) -> list:
    """{"a": [1, 2], "b": [3]} -> [{"a": 1, "b": 3}, {"a": 2, "b": 3}]"""
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def _setting_id(setting: dict) -> str:
    return "_".join(f"{k}-{v}" for k, v in setting.items()) or "default"


def run_sweep(env, config: dict, grid: dict, seeds, episodes: int, out_dir: str,
              max_steps: int = None, eval_every: int = None, eval_episodes: int = 2, final_eval_episodes: int = 3,
              verbose: bool = True) -> list:
    """Run the sweep on an already-built env (so SUMO's single TraCI
    connection is shared and reset between runs). Returns the ranked
    summary rows."""
    runs_dir = os.path.join(out_dir, "runs")
    os.makedirs(runs_dir, exist_ok=True)
    settings = expand_grid(grid)
    state_dim = env.state_size
    run_rows = []

    for si, setting in enumerate(settings, start=1):
        for seed in seeds:
            run_id = f"{_setting_id(setting)}_seed-{seed}"
            row_path = os.path.join(runs_dir, f"{run_id}_row.json")
            if os.path.exists(row_path):                      # finished in an earlier (interrupted) sweep
                with open(row_path) as f:
                    run_rows.append(json.load(f))
                if verbose:
                    print(f"[{si}/{len(settings)}] {run_id}  (already done, skipped)")
                continue
            cfg = copy.deepcopy(config)
            agent_params = {k: v for k, v in setting.items() if not k.startswith(REWARD_PREFIX)}
            reward_params = {k[len(REWARD_PREFIX):]: v for k, v in setting.items() if k.startswith(REWARD_PREFIX)}
            cfg.setdefault("dqn", {}).update(agent_params)
            cfg["dqn"]["seed"] = seed
            original_reward = {k: env.reward_cfg[k] for k in reward_params} if reward_params else {}
            if reward_params:
                env.reward_cfg.update(reward_params)
            agent = DQNAgent.from_config(cfg, state_dim=state_dim)
            if verbose:
                print(f"[{si}/{len(settings)}] {run_id}")
            history = {}
            try:
                train_agent(env, agent, episodes, max_steps=max_steps, verbose=False,
                            log_path=os.path.join(runs_dir, f"{run_id}.csv"),
                            eval_every=eval_every, eval_episodes=eval_episodes,
                            best_path=os.path.join(runs_dir, f"{run_id}_best.npz"), history=history)
                _write_evals(history.get("evals", []), os.path.join(runs_dir, f"{run_id}_evals.csv"))
                final = evaluate(env, agent, final_eval_episodes, max_steps=max_steps)
            finally:
                if reward_params:
                    env.reward_cfg.update(original_reward)   # never leak one setting's reward into the next
            row = {**setting, "seed": seed, **final, "best_episode": history.get("best_episode", "")}
            run_rows.append(row)
            with open(row_path, "w") as f:
                json.dump(row, f)
            if verbose:
                print("    final eval: " + "  ".join(f"{k}={final[k]:.2f}" for k in METRIC_KEYS if k in final))
                per = "  ".join(f"[{k.split('/')[0]}] wait={v:.1f}" for k, v in final.items()
                                if k.endswith("/mean_total_waiting"))
                if per:
                    print(f"    per scenario: {per}")

    return _write_outputs(run_rows, list(grid), out_dir)


def _write_evals(evals: list, path: str) -> None:
    """Each run's periodic greedy evaluations (episode + metrics): shows
    whether a run peaked and then drifted, which the final eval alone hides."""
    if not evals:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(evals[0]))
        writer.writeheader()
        writer.writerows(evals)


def _write_outputs(run_rows: list, setting_keys: list, out_dir: str) -> list:
    metrics = [k for k in METRIC_KEYS if k in run_rows[0]]
    metrics += sorted(k for k in run_rows[0] if "/" in k)   # per-scenario columns (mixed training)
    with open(os.path.join(out_dir, "sweep_runs.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)

    summary = []
    groups = {}
    for r in run_rows:
        groups.setdefault(tuple(r[k] for k in setting_keys), []).append(r)
    for key, rows in groups.items():
        entry = dict(zip(setting_keys, key))
        entry["n_seeds"] = len(rows)
        for m in metrics:
            vals = [r[m] for r in rows]
            entry[f"{m}_mean"] = statistics.fmean(vals)
            entry[f"{m}_std"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
        summary.append(entry)

    rank_key = "mean_total_waiting_mean" if "mean_total_waiting" in metrics else "reward_mean"
    summary.sort(key=lambda e: e[rank_key], reverse=rank_key == "reward_mean")
    with open(os.path.join(out_dir, "sweep_summary.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    return summary
