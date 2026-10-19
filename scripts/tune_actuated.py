"""Tune the density-responsive baseline on SELECTION seeds, so the comparison with the DQN is fair
(the DQN's settings were tuned the same way; test seeds are never used for tuning).

    python scripts/tune_actuated.py --scenarios tidal,rush_hour,low_traffic --episodes 20 --seed-base 20000

Evaluates every combination of min green / max green / switch ratio on each scenario (fixed timer as
reference), ranks combinations by the geometric-mean waiting across scenarios (a relative change counts the
same in light and heavy traffic), prints the best and writes tuning_actuated.csv. Confirm the winner on fresh
seeds with `traffic-drl compare`.
"""
import argparse
import csv
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traffic_drl.compare import run_comparison  # noqa: E402


def main(argv=None, env_factory=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="configs/dqn.yaml")
    ap.add_argument("--scenarios", default="tidal,rush_hour,low_traffic")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed-base", type=int, default=20000, help="selection seeds (not the test seeds 30000)")
    ap.add_argument("--min-green", default="10,15,20")
    ap.add_argument("--max-green", default="40,60,90")
    ap.add_argument("--ratio", default="1.5,2.5")
    ap.add_argument("--gap", default="0")
    ap.add_argument("--out-dir", default="results_tune_actuated")
    args = ap.parse_args(argv)

    grid = list(itertools.product(args.min_green.split(","), args.max_green.split(","),
                                  args.ratio.split(","), args.gap.split(",")))
    controllers = ["fixed"] + [f"a_min{mn}_max{mx}_r{r}_g{g}=actuated:min={mn},max={mx},ratio={r},gap={g}"
                               for mn, mx, r, g in grid]
    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    summary, _ = run_comparison(args.config, scenarios, controllers, episodes=args.episodes, seed_base=args.seed_base,
                                out_dir=args.out_dir, env_factory=env_factory)
    by_ctrl = {}
    for row in summary:
        by_ctrl.setdefault(row["controller"], {})[row["scenario"]] = row["mean"]
    ranked = sorted(((math.exp(sum(math.log1p(v) for v in d.values()) / len(d)) - 1, c, d) for c, d in by_ctrl.items()))
    print("\nranked by geometric-mean waiting (lower is better):")
    for score, c, d in ranked[:10]:
        print(f"  {c:32s} {score:7.2f}   " + "  ".join(f"{k}={v:.1f}" for k, v in d.items()))
    best = next(c for _, c, _ in ranked if c != "fixed")
    print(f"\nbest actuated setting: {best}")
    out = os.path.join(args.out_dir, "tuning_actuated.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["controller", "score", *scenarios])
        for score, c, d in ranked:
            w.writerow([c, f"{score:.3f}", *[f"{d[s]:.2f}" for s in d]])
    print(f"wrote {out}")
    return best


if __name__ == "__main__":
    main()
