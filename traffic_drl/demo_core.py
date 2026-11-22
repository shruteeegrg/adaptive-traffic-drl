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
    "Heavy, uneven 2:1 (800 per road on average)": "configs/scenarios/grid/grid_d800_r2.yaml",
    "Heavy, uneven 4:1": "configs/scenarios/grid/grid_d800_r4.yaml",
    "Heavy, uneven 8:1": "configs/scenarios/grid/grid_d800_r8.yaml",
    "Kathmandu mix, near capacity (motorcycles, buses, turns)": "configs/scenarios/rush_hour_kt.yaml",
    "Kathmandu mix, tidal": "configs/scenarios/tidal_kt.yaml",
    "Kathmandu mix, peak (slightly over capacity)": "configs/scenarios/kathmandu_peak.yaml",
}
CUSTOM = "Build your own traffic (set vehicles per road, vehicle mix, turns)"
GENERALIST = "models/gen_s3.npz"   # trained on 12 randomised demand patterns: the default agent for traffic it was not trained on
KEYS = ("fixed", "rule", "dqn")        # the three controllers shown side by side
CLI_CONTROLLER = {"fixed": "fixed", "rule": "actuated", "dqn": "dqn"}    # the names `traffic-drl run` accepts
CONTROLLERS = {"fixed": "Fixed-time (40 s per direction)", "rule": "Density rule (like Lalitpur's lights)",
               "dqn": "DQN agent"}
SHORT_NAMES = {"fixed": "Fixed-time", "rule": "Density rule", "dqn": "DQN agent"}   # chart legend labels
GRAY, BLUE, ORANGE = "#8a8985", "#2a78d6", "#eb6834"    # same colours as the report figures
COLORS = {"fixed": GRAY, "rule": ORANGE, "dqn": BLUE}
AUTO = "Best for this scenario (recommended)"
NEW_CONFIG, OLD_CONFIG = "configs/dqn_v_dqfd.yaml", "configs/dqn.yaml"
# The agent shown for each scenario. The models/ agents are the final ones (trained with demonstrations);
# each default is the one that scored best on the SELECTION seeds, not on the test seeds (models/manifest.json).
# Low traffic has no final specialist, so it keeps the earlier model trained on a mix of scenarios.
BEST_CHECKPOINT = {
    "configs/scenarios/tidal.yaml": ("models/dqfd_tidal_s3.npz", "trained on tidal traffic"),
    "configs/scenarios/rush_hour.yaml": ("models/dqfd_rush_s2.npz", "trained on rush-hour traffic"),
    "configs/scenarios/low_traffic.yaml": ("checkpoints/dqn_mixed.npz", "trained on a mix of scenarios"),
    "configs/scenarios/grid/grid_d800_r2.yaml": ("models/dqh_r2_s3.npz", "trained on this demand"),
    "configs/scenarios/grid/grid_d800_r4.yaml": ("models/dqh_r4_s0.npz", "trained on this demand"),
    "configs/scenarios/grid/grid_d800_r8.yaml": ("models/dqh_r8_s2.npz", "trained on this demand"),
    "configs/scenarios/rush_hour_kt.yaml": ("models/dqk_rush_s3.npz", "trained on this demand"),
    "configs/scenarios/tidal_kt.yaml": ("models/dqk_tidal_s1.npz", "trained on this demand"),
    "configs/scenarios/kathmandu_peak.yaml": ("models/dqk_peak_s1.npz", "trained on this demand"),
}


def config_for(checkpoint: str) -> str:
    """Each checkpoint must be loaded with the config it was trained with: the earlier ones in checkpoints/
    use the original state, everything else (models/ and client training jobs) the 15-input one."""
    return OLD_CONFIG if checkpoint.replace("\\", "/").startswith("checkpoints/") else NEW_CONFIG


def build_run_command(controller: str, scenario_yaml: str, checkpoint: str, seed: int,
                      delay: float, out_path: str) -> list:
    # fixed and rule do not use the trained state; they run with the same config so all three see the same traffic
    config = config_for(checkpoint) if controller == "dqn" else NEW_CONFIG
    cmd = [sys.executable, "-m", "traffic_drl.cli", "run", "--controller", CLI_CONTROLLER[controller],
           "--config", config, "--scenario", scenario_yaml, "--seed", str(seed),
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
    path = BEST_CHECKPOINT.get(scenario_yaml, (GENERALIST, ""))[0]      # unknown (custom) traffic: the generalist
    return path if (ROOT / path).exists() else "checkpoints/dqn_final.npz"


def align_series(series: dict):
    """One DataFrame from several {name: pandas.Series indexed by minutes}.

    The two controllers report at different simulated times (a decision that switches
    the light takes longer than one that keeps it), so their indexes differ. Joined
    naively, each line has gaps and the chart draws broken lines; interpolating inside
    each line's own range joins them up without inventing data beyond what was reached."""
    import pandas as pd

    df = pd.DataFrame(series).sort_index()
    return df.interpolate(method="index", limit_area="inside")


def list_checkpoints() -> list:
    paths = sorted(glob.glob(str(ROOT / "models" / "*.npz"))) + sorted(glob.glob(str(ROOT / "checkpoints" / "*.npz")))
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


def verdict_vs_rule(rule: dict, dqn: dict) -> str:
    """One honest sentence comparing the DQN with the density rule. Differences under 5% (or under 2 vehicles
    waiting) are called a tie: a single run cannot show more than that."""
    r, d = rule["mean_total_waiting"], dqn["mean_total_waiting"]
    if abs(d - r) < max(0.05 * r, 2.0):
        return f"The DQN agent and the density rule are about level here ({d:.1f} vs {r:.1f} vehicles waiting)."
    if d < r:
        return (f"The DQN agent had {abs(d - r) / r:.0%} fewer vehicles waiting than the density rule "
                f"({d:.1f} vs {r:.1f}) in this run. One run is a single sample: see the Test results tab for 100 runs.")
    return (f"Here the density rule did better: the DQN agent had {(d - r) / r:.0%} more vehicles waiting "
            f"({d:.1f} vs {r:.1f}).")


def final_results_markdown() -> str:
    """The consolidated table of the 100-episode comparisons (docs/results_final.md); empty if missing."""
    path = ROOT / "docs" / "results_final.md"
    return path.read_text() if path.exists() else ""


def custom_spec(name: str, rates: dict, minutes: float = 30, swap: bool = False, mix_pct: dict = None,
                turns_pct: dict = None) -> dict:
    """A junction spec (see traffic_drl.intake) from the playground's controls.

    rates     vehicles per hour per approach {"east", "north", "west", "south"}
    swap      the busy and quiet axes trade rates halfway (a tidal pattern), as two equal periods
    mix_pct   {"motorcycle", "car", "bus", "goods"} percentages (any positive total; normalised). All zero -> cars.
    turns_pct {"left", "right"} percentages of each approach turning
    """
    from traffic_drl import intake

    minutes = min(max(float(minutes), 1.0), 30.0)    # the evaluation episode is 30 minutes (episode_length)
    if swap:
        half = minutes / 2.0
        flipped = {"east": rates["north"], "north": rates["east"], "west": rates["south"], "south": rates["west"]}
        demand = [{"minutes": half, **rates}, {"minutes": half, **flipped}]
    else:
        demand = dict(rates)
    mix = {k: float(v) for k, v in (mix_pct or {}).items() if v and v > 0}
    spec = {"name": name, "demand": demand,
            "vehicle_mix": {k: v / sum(mix.values()) for k, v in mix.items()} if mix else "cars"}
    if not swap:
        spec["duration_minutes"] = minutes
    t = turns_pct or {}
    spec["turns"] = {"left": t.get("left", 0) / 100.0, "right": t.get("right", 0) / 100.0}
    return spec


def build_custom(spec: dict, out_dir: str) -> dict:
    """Validate and write the playground's traffic; returns intake's result (scenario_yaml, summary, advisories, context)."""
    from traffic_drl import intake

    return intake.build_scenario(spec, out_dir)
