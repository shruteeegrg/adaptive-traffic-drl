"""Head-to-head comparison of controllers on one or more scenarios, with statistics.

    traffic-drl compare --scenarios tidal,rush_hour,low_traffic \\
        --controller fixed --controller actuated --controller dqn=dqn:checkpoints/dqn_final.npz \\
        --episodes 100

Every controller is run on the same SUMO seeds (a fresh environment per
controller starts its seed counter at --seed-base), so episode i sees identical
traffic for all of them. For each non-reference controller the report gives
the mean of the chosen metric with a 95 percent confidence interval, the change
against the reference, a Welch (independent) and a paired t-test p-value,
Cohen's d, and a verdict that needs BOTH statistical and practical significance:

  better / worse   p < 0.05 and the change is at least `threshold` of the
                   reference mean and at least `min_abs` in absolute terms
  small            p < 0.05 but the change is below the practical threshold
  tie              not significant

Controller specs:  fixed[:GREEN_SECONDS]   actuated[:min=10,max=60,gap=1,ratio=1.5]   dqn:PATH
and an optional label:  NAME=SPEC
"""

import csv
import os

from traffic_drl import stats

PRIMARY = "mean_total_waiting"
SECONDARY = ("avg_wait_per_vehicle", "throughput_per_hour", "switches")
# default absolute floor for the practical-significance rule, per metric (vehicles, seconds, vehicles per hour)
MIN_ABS = {"mean_total_waiting": 2.0, "avg_wait_per_vehicle": 1.0, "throughput_per_hour": 50.0}


def parse_controller(spec: str):
    """'label=kind:arg' -> (label, kind, arg). The label defaults to the spec itself."""
    label, _, rest = spec.partition("=") if "=" in spec.split(":")[0] else ("", "", spec)
    kind, _, arg = rest.partition(":")
    if kind not in ("fixed", "actuated", "dqn"):
        raise ValueError(f"unknown controller '{kind}' in '{spec}'; use fixed, actuated or dqn")
    if kind == "dqn" and not arg:
        raise ValueError("dqn needs a checkpoint, e.g. dqn:checkpoints/dqn_final.npz")
    return (label or spec), kind, arg


def build_agent(kind: str, arg: str, config: dict, env):
    if kind == "fixed":
        from traffic_drl.baseline import FixedTimeAgent

        green = float(arg) if arg else 40.0
        return FixedTimeAgent(green_steps=max(1, round(green / env.decision_interval)))
    if kind == "actuated":
        from traffic_drl.baseline import DensityActuatedAgent

        params = {}
        aliases = {"min": "min_green", "max": "max_green", "gap": "gap_queue", "ratio": "ratio"}
        for item in filter(None, arg.split(",")):
            key, _, value = item.partition("=")
            if key not in aliases:
                raise ValueError(f"unknown actuated parameter '{key}'; use min, max, gap, ratio")
            params[aliases[key]] = float(value)
        return DensityActuatedAgent.from_config(config, **params).attach(env)
    from traffic_drl.agent import DQNAgent

    agent = DQNAgent.from_config(config, state_dim=env.state_size)
    try:
        agent.load(arg)
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot load checkpoint {arg}: {e}\n(is --config the config this checkpoint was trained with?)")
    return agent


def verdict(ref_mean: float, mean: float, p: float, threshold: float, min_abs: float) -> str:
    """Lower is better (vehicles waiting). Needs statistical AND practical significance."""
    if not p < 0.05:
        return "tie"
    change = mean - ref_mean
    practical = abs(change) >= max(threshold * abs(ref_mean), min_abs)
    if not practical:
        return "small"
    return "better" if change < 0 else "worse"


def resolve_scenario(name: str, config_path: str) -> str:
    """A scenario given by name (tidal) or by YAML path."""
    if os.path.exists(name):
        return name
    candidate = os.path.join(os.path.dirname(os.path.abspath(config_path)), "scenarios", f"{name}.yaml")
    if os.path.exists(candidate):
        return candidate
    raise SystemExit(f"scenario '{name}' not found (tried {name} and {candidate})")


def run_comparison(config_path, scenarios, controllers, episodes=100, seed_base=30000, out_dir="results_compare",
                   reference=None, threshold=0.05, min_abs=None, metric=PRIMARY, env_factory=None, log=print):
    from traffic_drl.agent import evaluate
    from traffic_drl.config import load_config

    if env_factory is None:
        from traffic_drl.env import TraciEnv

        env_factory = lambda cfg, sc: TraciEnv(cfg, scenario=sc)   # noqa: E731
    config = load_config(config_path)
    specs = [parse_controller(c) for c in controllers]
    labels = [s[0] for s in specs]
    if len(set(labels)) != len(labels):
        raise SystemExit(f"controller labels must be unique, got {labels}")
    reference = reference or labels[0]
    if reference not in labels:
        raise SystemExit(f"--reference {reference} is not one of {labels}")
    if min_abs is None:
        min_abs = MIN_ABS.get(metric, 0.0)
    os.makedirs(out_dir, exist_ok=True)

    episode_rows, summary = [], []
    for scenario in scenarios:
        sc_path = resolve_scenario(scenario, config_path)
        sc_name = os.path.splitext(os.path.basename(sc_path))[0]
        results = {}
        for label, kind, arg in specs:
            env = env_factory(config_path, sc_path)
            try:
                agent = build_agent(kind, arg, config, env)
                runs = []
                for _ in range(episodes):
                    if hasattr(agent, "reset"):
                        agent.reset()
                    runs.append(evaluate(env, agent, episodes=1, seed_base=seed_base))
            finally:
                env.close()
            results[label] = runs
            for i, r in enumerate(runs, start=1):
                episode_rows.append({"scenario": sc_name, "controller": label, "episode": i, **r})
            log(f"  {sc_name}: {label} done ({episodes} episodes)")
        ref_vals = [r[metric] for r in results[reference]]
        for label in labels:
            vals = [r[metric] for r in results[label]]
            m, half = stats.ci95(vals)
            row = {"scenario": sc_name, "controller": label, "n": len(vals), "metric": metric,
                   "mean": m, "ci95": half, "std": stats.sample_var(vals) ** 0.5}
            for k in SECONDARY:
                if k in results[label][0]:
                    row[k] = stats.mean(r[k] for r in results[label])
            if label == reference:
                row.update({"change_pct": 0.0, "p_welch": "", "p_paired": "", "cohens_d": "", "verdict": "reference"})
            else:
                welch = stats.welch_t_test(vals, ref_vals)
                paired = stats.paired_t_test(vals, ref_vals)
                row.update({"change_pct": 100.0 * (m - stats.mean(ref_vals)) / stats.mean(ref_vals) if stats.mean(ref_vals) else 0.0,
                            "p_welch": welch["p"], "p_paired": paired["p"], "cohens_d": stats.cohens_d(vals, ref_vals),
                            "verdict": verdict(stats.mean(ref_vals), m, welch["p"], threshold, min_abs)})
            summary.append(row)

    _write_csv(os.path.join(out_dir, "compare_episodes.csv"), episode_rows)
    _write_csv(os.path.join(out_dir, "compare_summary.csv"), summary)
    table = markdown_table(summary, reference, threshold, min_abs, episodes, seed_base, metric)
    with open(os.path.join(out_dir, "compare_summary.md"), "w") as f:
        f.write(table)
    return summary, table


def _write_csv(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _fmt_p(p):
    if p == "":
        return ""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def markdown_table(summary, reference, threshold, min_abs, episodes, seed_base, metric=PRIMARY) -> str:
    lines = [f"Metric: {metric} (lower is better). {episodes} episodes per cell, fresh seeds from "
             f"{seed_base}, the same traffic for every controller. Reference: {reference}. "
             f"Verdict needs p < 0.05 (Welch) and a change of at least {threshold:.0%} and {min_abs:g} (units of the metric).",
             "",
             "| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        change = "" if r["verdict"] == "reference" else f"{r['change_pct']:+.1f}%"
        d = "" if r["cohens_d"] == "" else f"{r['cohens_d']:+.2f}"
        lines.append(
            f"| {r['scenario']} | {r['controller']} | {r['mean']:.1f} +- {r['ci95']:.1f} | {change} | {_fmt_p(r['p_welch'])} | "
            f"{_fmt_p(r['p_paired'])} | {d} | {r.get('avg_wait_per_vehicle', float('nan')):.1f} | "
            f"{r.get('throughput_per_hour', float('nan')):.0f} | {r.get('switches', float('nan')):.0f} | {r['verdict']} |")
    return "\n".join(lines) + "\n"
