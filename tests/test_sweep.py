"""Week 6 tests: fixed-length-episode config, per-episode SUMO seeds,
evaluation / best checkpointing, and the sweep. No SUMO needed.
    python -m pytest tests/test_sweep.py -v     (or: python tests/test_sweep.py)
"""

import csv
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl.agent import DQNAgent, QTableAgent, evaluate, train_agent  # noqa: E402
from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import SimpleQueueEnv, traci_env  # noqa: E402
from traffic_drl.sweep import expand_grid, run_sweep  # noqa: E402
from test_state_reward import FakeTraci  # noqa: E402


def _toy():
    return SimpleQueueEnv(seed=0, state_scale=20, include_phase=True)


def test_expand_grid():
    grid = expand_grid({"a": [1, 2], "b": [3, 4, 5]})
    assert len(grid) == 6 and {"a": 2, "b": 4} in grid
    assert expand_grid({}) == [{}]


def test_dqn_config_uses_fixed_sim_time_episodes():
    cfg = load_config(os.path.join(ROOT, "configs", "dqn.yaml"))
    assert cfg["episode_length"] == 1800 and cfg["dqn"]["max_steps"] is None
    assert cfg["sweep"]["grid"]
    # eval_every lives in the dqn section but must not reach the constructor
    DQNAgent.from_config(cfg, state_dim=11)


def test_evaluate_is_greedy_and_does_not_learn():
    agent = QTableAgent(seed=0)
    train_agent(_toy(), agent, 3, verbose=False)
    snapshot = {k: v.copy() for k, v in agent.q.items()}
    eps = agent.epsilon
    result = evaluate(_toy(), agent, episodes=2)
    assert set(result) == {"reward"}
    assert all(np.array_equal(agent.q[k], v) for k, v in snapshot.items()) and agent.epsilon == eps


def test_train_saves_best_checkpoint_and_history():
    agent = DQNAgent(4, hidden_sizes=(8,), learn_start=50, seed=0)
    history = {}
    with tempfile.TemporaryDirectory() as d:
        best = os.path.join(d, "sub", "dqn_best.npz")
        train_agent(_toy(), agent, 4, verbose=False, eval_every=2, eval_episodes=1,
                    best_path=best, history=history)
        assert os.path.exists(best)
    assert [e["episode"] for e in history["evals"]] == [2, 4]
    assert history["best_episode"] in (2, 4)
    assert history["best_score"] == max(e["reward"] for e in history["evals"])


def test_sumo_seed_differs_per_episode_and_eval_uses_unseen_seeds():
    fake = FakeTraci()
    traci_env.traci = fake
    env = traci_env.TraciEnv(os.path.join(ROOT, "configs", "intersection.yaml"), seed=5)
    seeds = []
    for _ in range(3):
        env.reset()
        seeds.append(int(fake.cmd[fake.cmd.index("--seed") + 1]))
    assert seeds == [5, 6, 7]

    class Stub:  # always action 0, for evaluate()
        def act(self, s, greedy=False): return 0

    evaluate(env, Stub(), episodes=1, max_steps=2)
    assert int(fake.cmd[fake.cmd.index("--seed") + 1]) >= 10_000
    assert env.seed_base == 5  # restored for further training
    assert "mean_queue" in evaluate(env, Stub(), episodes=1, max_steps=2)


def test_evaluate_command_runs_a_checkpoint_and_rejects_wrong_config(capsys=None):
    import io
    import contextlib
    from traffic_drl import cli

    traci_env.traci = FakeTraci()
    with tempfile.TemporaryDirectory() as d:
        ckpt = os.path.join(d, "dqn.npz")
        DQNAgent(state_dim=11, hidden_sizes=(64, 64)).save(ckpt)   # matches configs/dqn.yaml
        dqn_cfg = os.path.join(ROOT, "configs", "dqn.yaml")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["evaluate", "--checkpoint", ckpt, "--config", dqn_cfg, "--episodes", "2",
                             "--scenario", os.path.join(ROOT, "configs", "scenarios", "rush_hour.yaml")])
        text = out.getvalue()
        assert code == 0 and "mean:" in text and "mean_total_waiting=" in text and "episode 2:" in text
        # a checkpoint trained with a different state design must fail loudly, not silently misread
        try:
            cli.main(["evaluate", "--checkpoint", ckpt, "--episodes", "1",
                      "--config", os.path.join(ROOT, "configs", "dqn_backlog.yaml")])
        except SystemExit as e:
            assert "sizes" in str(e)
        else:
            raise AssertionError("expected SystemExit for mismatched architecture")


def test_evaluate_command_scores_every_best_checkpoint_in_a_folder():
    import io
    import contextlib
    from traffic_drl import cli

    traci_env.traci = FakeTraci()
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "runs"))
        for i in range(2):
            DQNAgent(state_dim=11, hidden_sizes=(64, 64), seed=i).save(os.path.join(d, "runs", f"r{i}_best.npz"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["evaluate", "--checkpoint", d, "--config", os.path.join(ROOT, "configs", "dqn.yaml"),
                             "--episodes", "1"])
        rows = list(csv.DictReader(open(os.path.join(d, "best_checkpoints_eval.csv"))))
    assert code == 0 and len(rows) == 2 and "ranked by mean_total_waiting" in out.getvalue()
    assert {r["checkpoint"] for r in rows} == {os.path.join("runs", "r0_best.npz"), os.path.join("runs", "r1_best.npz")}


def test_evaluate_and_baseline_accept_a_fresh_seed_base():
    import io
    import contextlib
    from traffic_drl import cli

    fake = FakeTraci()
    traci_env.traci = fake
    dqn_cfg = os.path.join(ROOT, "configs", "dqn.yaml")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        cli.main(["baseline", "--config", dqn_cfg, "--episodes", "1", "--seed-base", "20000"])
    assert int(fake.cmd[fake.cmd.index("--seed") + 1]) >= 20000
    assert "seeds from 20000" in out.getvalue()


def test_sweep_writes_ranked_outputs():
    cfg = {"dqn": {"hidden_sizes": [8], "learn_start": 50, "batch_size": 16}}
    with tempfile.TemporaryDirectory() as d:
        summary = run_sweep(_toy(), cfg, {"learning_rate": [0.001, 0.003], "gamma": [0.9]},
                            seeds=[0, 1], episodes=3, out_dir=d, max_steps=60,
                            eval_every=3, final_eval_episodes=1, verbose=False)
        runs = list(csv.DictReader(open(os.path.join(d, "sweep_runs.csv"))))
        ranked = list(csv.DictReader(open(os.path.join(d, "sweep_summary.csv"))))
        files = os.listdir(os.path.join(d, "runs"))
    assert len(runs) == 4 and len(summary) == len(ranked) == 2
    assert [float(r["reward_mean"]) for r in ranked] == sorted((float(r["reward_mean"]) for r in ranked), reverse=True)
    assert all(r["n_seeds"] == "2" for r in ranked)
    assert sum(f.endswith("_best.npz") for f in files) == 4
    assert sum(f.endswith("_evals.csv") for f in files) == 4   # per-run evaluation history


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
