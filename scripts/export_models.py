#!/usr/bin/env python3
"""Copy the final trained agents into models/ (tracked in git) and write models/manifest.json.

    python scripts/export_models.py

Every independently trained Double-DQN agent of each final sweep is copied (checkpoints/ is git-ignored).
The default agent for a scenario is the one with the lowest score on the SELECTION seeds (the sweep's
final re-evaluation on seeds 20000+), never the one that did best on the 100-episode test seeds, so the
default is not picked with the test set. The test results for all agents are in docs/results_final.md.
"""
import csv
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = "configs/dqn_v_dqfd.yaml"     # the state design shared by every final agent
# (model name, results folder of the sweep, scenario yaml it was trained on)
MODELS = [
    ("dqfd_tidal", "results/sweeps/vd_tidal", "configs/scenarios/tidal.yaml"),
    ("dqfd_rush", "results/sweeps/vd_rush", "configs/scenarios/rush_hour.yaml"),
    ("dqh_r2", "results/sweeps/vh_r2", "configs/scenarios/grid/grid_d800_r2.yaml"),
    ("dqh_r4", "results/sweeps/vh_r4", "configs/scenarios/grid/grid_d800_r4.yaml"),
    ("dqh_r8", "results/sweeps/vh_r8", "configs/scenarios/grid/grid_d800_r8.yaml"),
    ("dqk_tidal", "results/sweeps/vk_tidal", "configs/scenarios/tidal_kt.yaml"),
    ("dqk_rush", "results/sweeps/vk_rush", "configs/scenarios/rush_hour_kt.yaml"),
    ("dqk_peak", "results/sweeps/vk_peak", "configs/scenarios/kathmandu_peak.yaml"),
    ("gen", "results/sweeps/vg", "configs/scenarios/pool (12 randomised patterns)"),
]


def agents_of(folder: str) -> list:
    """[(seed, selection score, path)] for the Double-DQN runs of a sweep."""
    rows = list(csv.DictReader(open(os.path.join(ROOT, folder, "sweep_runs.csv"))))
    out = []
    for r in rows:
        if r["double_dqn"] not in ("True", "true"):
            continue
        seed = int(float(r["seed"]))
        pattern = (f"learning_rate-{r['learning_rate']}_target_sync_steps-{r['target_sync_steps']}_epsilon_decay-{r['epsilon_decay']}"
                   f"_gamma-{r['gamma']}_double_dqn-True_seed-{seed}_best.npz")
        out.append((seed, float(r["mean_total_waiting"]), os.path.join(ROOT, folder, "runs", pattern)))
    return sorted(out)


def export(root=ROOT, models=MODELS, out_dir=None) -> dict:
    out_dir = out_dir or os.path.join(root, "models")
    os.makedirs(out_dir, exist_ok=True)
    manifest = {"config": CONFIG, "models": {}}
    for name, folder, scenario in models:
        agents = agents_of(folder)
        if not agents:
            raise SystemExit(f"no Double-DQN runs in {folder}")
        default_seed = min(agents, key=lambda a: a[1])[0]
        files = []
        for seed, score, path in agents:
            if not os.path.exists(path):
                raise SystemExit(f"missing checkpoint {path}")
            target = f"{name}_s{seed}.npz"
            shutil.copyfile(path, os.path.join(out_dir, target))
            files.append({"file": f"models/{target}", "seed": seed, "selection_score": round(score, 2)})
        manifest["models"][name] = {"scenario": scenario, "source": folder, "default": f"models/{name}_s{default_seed}.npz",
                                    "agents": files}
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    return manifest


if __name__ == "__main__":
    m = export()
    for name, info in m["models"].items():
        print(f"{name:11s} default {info['default']}  ({len(info['agents'])} agents)")
