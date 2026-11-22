"""The advisor: evaluate a junction's traffic under the candidate controllers and recommend one.

One call, `advise(...)`, runs the controllers on the same traffic (same SUMO seeds), tests each against the
client's current practice (a fixed timer), and returns a structured `Advice` dict that a report, a web page or
an API can render. The decision rule is deliberately conservative:

  * current practice is the reference: nothing is recommended unless it is significantly AND meaningfully
    better than the fixed timer (the same two-part test as `compare`);
  * the density rule is the default recommendation, because it is simple, transparent and cheap to run;
  * a trained DQN is recommended instead only if it also beats the density rule by the same test.

Every recommendation carries the evidence behind it, the settings to apply and the caveats that limit it.
"""

import json
import os

from traffic_drl import compare, stats

FIXED_LABEL, RULE_LABEL, DQN_LABEL = "fixed", "rule", "dqn"
DEFAULT_CONFIG = "configs/dqn_v_dqfd.yaml"
DEFAULT_FIXED_GREEN = 40
DEFAULT_RULE = {"min": 10, "max": 40, "ratio": 4, "gap": 0}   # tuned on cars-only traffic (see README limits)
MIN_EPISODES_FOR_CONFIDENCE = 30
LIMITS = [
    "Results are from simulation of a single four-way junction with one lane per road and two signal phases.",
    "The density rule's settings were tuned on cars-only traffic; mixed traffic (motorcycles, buses) may favour "
    "different settings.",
    "A simulation compares controllers on the same assumed traffic. Check the result against real counts after rollout.",
]


def rule_spec(params: dict = None) -> str:
    p = {**DEFAULT_RULE, **(params or {})}
    return "actuated:" + ",".join(f"{k}={p[k]}" for k in ("min", "max", "ratio", "gap"))


def _better(candidate_vals, ref_vals, threshold=0.05, min_abs=compare.MIN_ABS[compare.PRIMARY]) -> dict:
    """Is `candidate` significantly and meaningfully lower (better) than `ref`? Same rule as compare.verdict."""
    t = stats.welch_t_test(candidate_vals, ref_vals)
    v = compare.verdict(stats.mean(ref_vals), stats.mean(candidate_vals), t["p"], threshold, min_abs)
    return {"verdict": v, "p": t["p"]}


def recommend(summary: list, episode_rows: list, load_notes=None, metric: str = compare.PRIMARY) -> dict:
    """Pure decision logic over a comparison's summary rows and per-episode rows (one scenario).
    Returns the Advice dict (without the settings/files that `advise` adds)."""
    rows = {r["controller"]: r for r in summary}
    if FIXED_LABEL not in rows:
        raise ValueError("the comparison must include the fixed timer (the client's current practice)")
    fixed = rows[FIXED_LABEL]
    n = fixed["n"]
    candidates = [c for c in rows if c != FIXED_LABEL]
    wins = [c for c in candidates if rows[c]["verdict"] == "better"]
    vals = lambda c: [e[metric] for e in episode_rows if e["controller"] == c]   # noqa: E731

    reasons = []
    if not wins:
        choice = FIXED_LABEL
        reasons.append("No tested alternative reduced waiting significantly and meaningfully against the fixed timer.")
    else:
        choice = min(wins, key=lambda c: rows[c]["mean"])
        if choice.startswith(DQN_LABEL) and RULE_LABEL in rows:
            vs_rule = _better(vals(choice), vals(RULE_LABEL))
            if vs_rule["verdict"] != "better":
                reasons.append(f"The learned controller '{choice}' does not beat the simpler density rule "
                               f"significantly and meaningfully (verdict: {vs_rule['verdict']}), so the rule is recommended.")
                choice = RULE_LABEL if RULE_LABEL in wins else FIXED_LABEL
            else:
                reasons.append(f"The learned controller '{choice}' beats both the fixed timer and the density rule.")
    chosen = rows[choice]
    change = 0.0 if choice == FIXED_LABEL else chosen["change_pct"]
    if choice != FIXED_LABEL and not reasons:
        reasons.append(f"{choice} is significantly and meaningfully better than the fixed timer ({change:+.1f}%).")

    if n < MIN_EPISODES_FOR_CONFIDENCE:
        confidence = "preliminary"
        reasons.append(f"Only {n} episodes per controller were run; use at least {MIN_EPISODES_FOR_CONFIDENCE} "
                       "(100 recommended) before acting on this.")
    else:
        confidence = "firm" if choice != FIXED_LABEL else "firm (no change recommended)"

    evidence = []
    for c in [FIXED_LABEL] + candidates:
        r = rows[c]
        evidence.append({"controller": c, "mean_waiting": r["mean"], "ci95": r["ci95"], "n": r["n"],
                         "change_vs_fixed_pct": 0.0 if c == FIXED_LABEL else r["change_pct"],
                         "p_welch": None if c == FIXED_LABEL else r["p_welch"], "verdict": r["verdict"],
                         "wait_per_vehicle_s": r.get("avg_wait_per_vehicle"), "vehicles_per_hour": r.get("throughput_per_hour"),
                         "switches": r.get("switches")})
    return {"recommended": choice, "change_vs_fixed_pct": change, "confidence": confidence, "reasons": reasons,
            "evidence": evidence, "caveats": list(load_notes or []) + LIMITS, "episodes": n}


def headline(advice: dict) -> str:
    c = advice["recommended"]
    if c == FIXED_LABEL:
        return "Keep the current fixed timer: no alternative was clearly better on this traffic."
    what = "the density-responsive rule" if c == RULE_LABEL else f"the learned controller '{c}'"
    return (f"Use {what}: {abs(advice['change_vs_fixed_pct']):.0f}% fewer vehicles waiting than the fixed timer "
            f"({advice['confidence']}, {advice['episodes']} simulated runs each).")


def settings_for(choice: str, controllers: list) -> dict:
    """What to apply. For the rule: its parameters; for the fixed timer: its green time; for a DQN: its model file."""
    for label, kind, arg in (compare.parse_controller(c) for c in controllers):
        if label != choice:
            continue
        if kind == "fixed":
            return {"controller": "fixed timer", "green_seconds_per_direction": float(arg or DEFAULT_FIXED_GREEN)}
        if kind == "actuated":
            p = dict(item.split("=") for item in arg.split(",") if item)
            return {"controller": "density-responsive rule",
                    "minimum_green_seconds": float(p["min"]), "maximum_green_seconds": float(p["max"]),
                    "switch_when_other_road_has_more_than_x_times_the_vehicles": float(p["ratio"]),
                    "switch_when_current_road_has_at_most_vehicles": float(p["gap"]),
                    "how_it_works": "Keep green at least the minimum; then give green to the road with more vehicles "
                                    "on the approach (all vehicles counted, moving ones included), switching early "
                                    "if the current road empties and never holding past the maximum while the other "
                                    "road waits."}
        return {"controller": "learned controller (DQN)", "model_file": arg.partition("@")[0]}
    raise ValueError(f"no controller labelled {choice}")


def advise(scenario_yaml: str, out_dir: str, config: str = DEFAULT_CONFIG, episodes: int = 100, seed_base: int = 30000,
           dqn: dict = None, rule_params: dict = None, fixed_green: float = DEFAULT_FIXED_GREEN, load_notes=None,
           env_factory=None, log=print) -> dict:
    """Run the candidates on `scenario_yaml` and return the Advice dict (also written to out_dir/advice.json).
    `dqn` maps a label to a checkpoint ('path' or 'path@config'): only agents trained for this junction's
    demand belong here; a model trained on other traffic is not a fair candidate."""
    controllers = [f"{FIXED_LABEL}=fixed:{fixed_green:g}", f"{RULE_LABEL}={rule_spec(rule_params)}"]
    for label, ckpt in (dqn or {}).items():
        if not label.startswith(DQN_LABEL):
            raise ValueError(f"learned-controller labels must start with '{DQN_LABEL}', got '{label}'")
        controllers.append(f"{label}=dqn:{ckpt}")
    episode_rows = []
    summary, table = compare.run_comparison(config, [scenario_yaml], controllers, episodes=episodes, seed_base=seed_base,
                                            out_dir=out_dir, reference=FIXED_LABEL, env_factory=env_factory, log=log,
                                            episode_rows_out=episode_rows)
    advice = recommend(summary, episode_rows, load_notes)
    advice["headline"] = headline(advice)
    advice["settings"] = settings_for(advice["recommended"], controllers)
    advice["scenario"] = os.path.splitext(os.path.basename(scenario_yaml))[0]
    advice["table_markdown"] = table
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "advice.json"), "w") as f:
        json.dump(advice, f, indent=2)
    return advice
