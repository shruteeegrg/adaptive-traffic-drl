"""Hyperparameter sweep for the DQN agent (Week 6).

Trains every combination of the grid x every seed on one scenario, scores
each trained agent with a greedy evaluation on unseen SUMO seeds, and
writes:
  sweep_runs.csv      one row per (setting, seed)
  sweep_summary.csv   one row per setting: mean/std over seeds, ranked
  runs/<id>_best.npz  best-so-far checkpoint of each run
  runs/<id>.csv       each run's training log (reward curve + metrics)
Ranking uses mean_total_waiting (average halted vehicles plus vehicles
stuck waiting to enter the network, lower is better): total delay at fixed
demand per simulated second, valid even when demand overloads the junction.
The other metrics are reported alongside. Where the env has no metrics (the toy
model), reward is used instead.
"""

import copy
import csv
import itertools
import os
import statistics

from traffic_drl.agent import DQNAgent, evaluate, train_agent

METRIC_KEYS = ("reward", "mean_total_waiting", "mean_queue", "mean_backlog",
               "avg_wait_per_vehicle", "throughput_per_hour")


def expand_grid(grid: dict) -> list:
    """{"a": [1, 2], "b": [3]} -> [{"a": 1, "b": 3}, {"a": 2, "b": 3}]"""
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def _setting_id(setting: dict) -> str:
    return "_".join(f"{k}-{v}" for k, v in setting.items()) or "default"


def run_sweep(env, config: dict, grid: dict, seeds, episodes: int, out_dir: str,
              max_steps: int = None, eval_every: int = None, final_eval_episodes: int = 3,
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
            cfg = copy.deepcopy(config)
            cfg.setdefault("dqn", {}).update(setting)
            cfg["dqn"]["seed"] = seed
            agent = DQNAgent.from_config(cfg, state_dim=state_dim)
            if verbose:
                print(f"[{si}/{len(settings)}] {run_id}")
            history = {}
            train_agent(env, agent, episodes, max_steps=max_steps, verbose=False,
                        log_path=os.path.join(runs_dir, f"{run_id}.csv"),
                        eval_every=eval_every, best_path=os.path.join(runs_dir, f"{run_id}_best.npz"),
                        history=history)
            final = evaluate(env, agent, final_eval_episodes, max_steps=max_steps)
            row = {**setting, "seed": seed, **final, "best_episode": history.get("best_episode", "")}
            run_rows.append(row)
            if verbose:
                print("    final eval: " + "  ".join(f"{k}={final[k]:.2f}" for k in METRIC_KEYS if k in final))

    return _write_outputs(run_rows, list(grid), out_dir)


def _write_outputs(run_rows: list, setting_keys: list, out_dir: str) -> list:
    metrics = [k for k in METRIC_KEYS if k in run_rows[0]]
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
