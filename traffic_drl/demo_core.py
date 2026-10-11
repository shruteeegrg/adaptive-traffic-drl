"""Logic behind the Streamlit demo, kept free of Streamlit so it is testable.

The app launches `traffic-drl run` once per controller (same scenario, same
SUMO seed, so the comparison is fair), then polls each process's JSON-lines
file and redraws.
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = {
    "Tidal (heavy one way, then the other)": "configs/scenarios/tidal.yaml",
    "Rush hour (heavy everywhere)": "configs/scenarios/rush_hour.yaml",
    "Low traffic": "configs/scenarios/low_traffic.yaml",
}
CONTROLLERS = {"fixed": "Fixed-time (40 s per direction)", "dqn": "DQN agent"}
SHORT_NAMES = {"fixed": "Fixed-time", "dqn": "DQN agent"}   # chart legend labels
GRAY, BLUE = "#8a8985", "#2a78d6"    # same colours as the report figures
AUTO = "Best for this scenario (recommended)"
# Checkpoint that did best on fresh seeds for each scenario (see logs/week-06.md).
BEST_CHECKPOINT = {
    "configs/scenarios/tidal.yaml": ("checkpoints/dqn_final.npz", "trained on tidal traffic"),
    "configs/scenarios/rush_hour.yaml": ("checkpoints/dqn_rush.npz", "trained on rush-hour traffic"),
    "configs/scenarios/low_traffic.yaml": ("checkpoints/dqn_mixed.npz", "trained on a mix of scenarios"),
}
RESULT_SCENARIOS = {"tidal": "Tidal", "rush": "Rush hour", "low": "Low traffic"}


def build_run_command(controller: str, scenario_yaml: str, checkpoint: str, seed: int,
                      delay: float, out_path: str) -> list:
    cmd = [sys.executable, "-m", "traffic_drl.cli", "run", "--controller", controller,
           "--config", "configs/dqn.yaml", "--scenario", scenario_yaml, "--seed", str(seed),
           "--delay", str(delay), "--out", out_path]
    if controller == "dqn":
        cmd += ["--checkpoint", checkpoint]
    return cmd


def launch(cmd: list, err_path: str) -> subprocess.Popen:
    """Start a run in the repo root; stderr goes to a file so a crash can be shown."""
    return subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=open(err_path, "w"))


def read_new_events(path: str, offset: int):
    """Complete JSON lines written since `offset`. A half-written last line is
    left for the next poll. Returns (events, new_offset)."""
    if not os.path.exists(path):
        return [], offset
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read()
    end = chunk.rfind(b"\n")
    if end < 0:
        return [], offset
    events = [json.loads(line) for line in chunk[:end].decode().splitlines() if line.strip()]
    return events, offset + end + 1


def resolve_checkpoint(choice: str, scenario_yaml: str) -> str:
    """The sidebar's "best for this scenario" option picks the checkpoint that tested best
    there; anything else is used as chosen. Falls back to the shipped tidal model."""
    if choice != AUTO:
        return choice
    path = BEST_CHECKPOINT.get(scenario_yaml, ("checkpoints/dqn_final.npz", ""))[0]
    return path if (ROOT / path).exists() else "checkpoints/dqn_final.npz"


def list_checkpoints() -> list:
    paths = sorted(glob.glob(str(ROOT / "checkpoints" / "*.npz")))
    return [os.path.relpath(p, ROOT) for p in paths]


def tail(path: str, n: int = 8) -> str:
    try:
        return "\n".join(Path(path).read_text().strip().splitlines()[-n:])
    except OSError:
        return ""


def verdict(fixed: dict, dqn: dict) -> str:
    """One honest sentence comparing the two finished runs."""
    f, d = fixed["mean_total_waiting"], dqn["mean_total_waiting"]
    if f < 0.5 and d < 0.5:
        return "Both controllers kept almost every vehicle moving; there is nothing to separate them."
    change = (d - f) / max(f, 1e-9)
    tp = dqn["throughput_per_hour"] - fixed["throughput_per_hour"]
    if change <= -0.05:
        return (f"The DQN agent had {abs(change):.0%} fewer vehicles waiting on average than the fixed timer "
                f"({d:.1f} vs {f:.1f}) and moved {tp:+.0f} vehicles per hour.")
    if change >= 0.05:
        return (f"Here the fixed timer did better: the DQN agent had {change:.0%} more vehicles waiting "
                f"({d:.1f} vs {f:.1f}) and moved {tp:+.0f} vehicles per hour.")
    return f"About the same: {d:.1f} vehicles waiting for the DQN agent vs {f:.1f} for the fixed timer."


def results_table() -> list:
    """Rows from the saved test runs in figures/*.csv (10 unseen-seed episodes each).
    Empty if the files are not there."""
    import csv

    rows = []
    for key, label in RESULT_SCENARIOS.items():
        base = ROOT / "figures" / f"{key}_baseline.csv"
        dqn = ROOT / "figures" / f"{key}_best.csv"          # best checkpoint for this scenario
        if not dqn.exists():
            dqn = ROOT / "figures" / f"{key}_dqn.csv"
        if not (base.exists() and dqn.exists()):
            continue

        def mean(path, col):
            vals = [float(r[col]) for r in csv.DictReader(open(path)) if r.get(col) not in (None, "")]
            return sum(vals) / len(vals)

        rows.append({
            "Scenario": label,
            "Waiting, fixed-time": round(mean(base, "mean_total_waiting"), 1),
            "Waiting, DQN": round(mean(dqn, "mean_total_waiting"), 1),
            "Vehicles/hour, fixed-time": round(mean(base, "throughput_per_hour")),
            "Vehicles/hour, DQN": round(mean(dqn, "throughput_per_hour")),
        })
    return rows
