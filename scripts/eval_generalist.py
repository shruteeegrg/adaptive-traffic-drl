#!/usr/bin/env python3
"""The final exam for a generalist candidate: the untouched test pool, test seeds (30000+), four controllers.

    python scripts/eval_generalist.py --candidate runs/gen2/h128_s1/best.npz --episodes 10 --out-dir runs/gen2/test

Controllers: the fixed timer, the density rule, the previous generalist (models/gen_s3.npz) and the candidate. One
`traffic-drl compare` process per test scenario, several at a time. The candidate must have been chosen on the
select pool BEFORE this is run; running it on several candidates and keeping the best would turn the test into a
second selection. Writes summary.md and summary.json.
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from traffic_drl import compare, stats  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CONFIG = "configs/dqn_v_dqfd.yaml"
OLD = "models/gen_s3.npz"


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--pool", default="configs/scenarios/client_pool/test")
    args = ap.parse_args()

    scenarios = sorted(p for p in os.listdir(os.path.join(ROOT, args.pool)) if p.endswith(".yaml"))
    controllers = ["--controller", "fixed=fixed:40", "--controller", "rule=actuated:min=10,max=40,ratio=4,gap=0",
                   "--controller", f"old=dqn:{OLD}@{CONFIG}", "--controller", f"new=dqn:{os.path.abspath(args.candidate)}@{CONFIG}"]
    running, queue = [], list(scenarios)
    while queue or running:
        running = [(n, p) for n, p in running if p.poll() is None]
        while queue and len(running) < args.workers:
            name = queue.pop(0)
            out = os.path.join(args.out_dir, name[:-5])
            os.makedirs(out, exist_ok=True)
            cmd = [sys.executable, "-m", "traffic_drl.cli", "compare", "--config", CONFIG, "--scenarios",
                   os.path.join(args.pool, name), *controllers, "--reference", "rule", "--episodes", str(args.episodes),
                   "--seed-base", "30000", "--out-dir", out]
            running.append((name, subprocess.Popen(cmd, cwd=ROOT, stdout=open(os.path.join(out, "log.txt"), "w"),
                                                   stderr=subprocess.STDOUT)))
        time.sleep(2)

    labels = ("fixed", "rule", "old", "new")
    rows, per = [], {}
    for name in scenarios:
        out = os.path.join(args.out_dir, name[:-5])
        summary, episodes = read_csv(os.path.join(out, "compare_summary.csv")), read_csv(os.path.join(out, "compare_episodes.csv"))
        by = {r["controller"]: r for r in summary}
        vals = {c: [float(e["mean_total_waiting"]) for e in episodes if e["controller"] == c] for c in labels}
        new_vs_old = stats.welch_t_test(vals["new"], vals["old"])
        verdict = compare.verdict(stats.mean(vals["old"]), stats.mean(vals["new"]), new_vs_old["p"], 0.05, 2.0)
        per[name[:-5]] = {"mean": {c: stats.mean(vals[c]) for c in labels}, "verdict_vs_rule": {c: by[c]["verdict"] for c in labels},
                          "new_vs_old": verdict}
        rows.append((name[:-5], per[name[:-5]]))

    def gmean_ratio(c, ref):
        return math.exp(sum(math.log((v["mean"][c] + 1) / (v["mean"][ref] + 1)) for _, v in rows) / len(rows)) - 1

    lines = [f"Test pool: {len(rows)} scenarios, {args.episodes} episodes per controller each, test seeds from 30000. "
             "Mean vehicles waiting (lower is better). Verdicts need p < 0.05 and a 5% / 2-vehicle change.", "",
             "| Scenario | Fixed | Rule | Old generalist | New agent | New vs rule | New vs old |", "|---|---|---|---|---|---|---|"]
    for name, v in rows:
        m = v["mean"]
        lines.append(f"| {name} | {m['fixed']:.1f} | {m['rule']:.1f} | {m['old']:.1f} | {m['new']:.1f} | "
                     f"{v['verdict_vs_rule']['new']} | {v['new_vs_old']} |")
    tally = lambda key, c, w: sum(1 for _, v in rows if v[key][c] == w) if key != "new_vs_old" else sum(1 for _, v in rows if v[key] == w)  # noqa: E731
    lines += ["", f"New agent vs rule: better in {tally('verdict_vs_rule', 'new', 'better')}, tie or small in "
              f"{tally('verdict_vs_rule', 'new', 'tie') + tally('verdict_vs_rule', 'new', 'small')}, worse in {tally('verdict_vs_rule', 'new', 'worse')} scenarios.",
              f"Old generalist vs rule: better in {tally('verdict_vs_rule', 'old', 'better')}, tie or small in "
              f"{tally('verdict_vs_rule', 'old', 'tie') + tally('verdict_vs_rule', 'old', 'small')}, worse in {tally('verdict_vs_rule', 'old', 'worse')}.",
              f"New agent vs old generalist: better in {tally('new_vs_old', None, 'better')}, tie or small in "
              f"{tally('new_vs_old', None, 'tie') + tally('new_vs_old', None, 'small')}, worse in {tally('new_vs_old', None, 'worse')}.",
              "", "Geometric mean change in waiting (relative to the rule): "
              f"fixed {gmean_ratio('fixed', 'rule'):+.1%}, old generalist {gmean_ratio('old', 'rule'):+.1%}, new agent {gmean_ratio('new', 'rule'):+.1%}.",
              f"New agent vs old generalist: {gmean_ratio('new', 'old'):+.1%}."]
    with open(os.path.join(args.out_dir, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(args.out_dir, "summary.json"), "w") as f:
        json.dump({"candidate": args.candidate, "episodes": args.episodes, "scenarios": per}, f, indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
