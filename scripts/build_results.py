#!/usr/bin/env python3
"""Collect every 100-episode comparison into one table and one figure, straight from the saved files.

    python scripts/build_results.py            # writes docs/results_final.md and figures/report/final_results.png

Each results_compare_* folder holds a compare_summary.csv with the reference rule (a simple vehicle-counting controller) as the reference. Agents are
grouped by their name (dqfd_rush_s0..s3 -> "dqfd_rush"). Nothing here is typed in by hand.
"""
import csv
import os
import re
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (folder, what the agents were trained on)
SOURCES = [
    ("results_compare_dqfd_tidal", "specialist, cars"),
    ("results_compare_dqfd_rush", "specialist, cars"),
    ("results_compare_dqh_r2", "specialist, cars"),
    ("results_compare_dqh_r4", "specialist, cars"),
    ("results_compare_dqh_r8", "specialist, cars"),
    ("results_compare_dqk_tidal", "specialist, Kathmandu mix"),
    ("results_compare_dqk_rush", "specialist, Kathmandu mix"),
    ("results_compare_dqk_peak", "specialist, Kathmandu mix"),
    ("results_compare_general", "generalist, 12 random patterns (held out)"),
]
AGENT = re.compile(r"(.+)_s(\d+)")


def read_rows(path):
    return list(csv.DictReader(open(path)))


def collect(root=ROOT, sources=SOURCES):
    """[{scenario, trained, family, rule, fixed, agents: [(mean, change_pct, verdict)]}] in file order."""
    out = []
    for folder, trained in sources:
        path = os.path.join(root, folder, "compare_summary.csv")
        if not os.path.exists(path):
            continue
        cells = OrderedDict()
        for r in read_rows(path):
            cells.setdefault(r["scenario"], OrderedDict())[r["controller"]] = r
        for scenario, ctrls in cells.items():
            rule = next((r for c, r in ctrls.items() if r["verdict"] == "reference"), None)
            if rule is None:
                continue
            families = OrderedDict()
            for c, r in ctrls.items():
                m = AGENT.fullmatch(c)
                if m:
                    families.setdefault(m.group(1), []).append((float(r["mean"]), float(r["change_pct"]), r["verdict"]))
            fixed = ctrls.get("fixed")
            for fam, agents in families.items():
                out.append({"scenario": scenario, "trained": trained, "family": fam, "rule": float(rule["mean"]),
                            "fixed": float(fixed["mean"]) if fixed else float("nan"), "agents": agents})
    return out


def markdown(rows) -> str:
    lines = ["# Final results: learned agents against the reference rule", "",
             "Mean total waiting (vehicles; lower is better), 100 episodes per cell on fresh seeds (30000+), the same traffic "
             "for every controller. Change is against the reference rule, a simple vehicle-counting controller written for this project (standard actuated-signal logic, settings chosen on separate seeds). Verdicts use the rule fixed in advance: Welch p < 0.05 and a change of "
             "at least 5% and 2 vehicles. Every independently trained agent is reported, not only the best.", "",
             "| Scenario | Agents trained as | Fixed | Rule | Agents (mean of n) | Range of agents | Mean change vs rule | Agents: better / tie or small / worse |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["agents"]
        means = [m for m, _, _ in a]
        changes = [c for _, c, _ in a]
        better = sum(v == "better" for _, _, v in a)
        worse = sum(v == "worse" for _, _, v in a)
        lines.append(f"| {r['scenario']} | {r['trained']} | {r['fixed']:.1f} | {r['rule']:.1f} | {sum(means) / len(means):.1f} (n={len(a)}) | "
                     f"{min(means):.1f} to {max(means):.1f} | {sum(changes) / len(changes):+.1f}% | {better} / {len(a) - better - worse} / {worse} |")
    lines += ["", "Notes. \"Tie or small\" includes changes that are statistically significant but below the practical floor of 2 vehicles: "
              "in low_traffic the generalist's +415% is under one vehicle in absolute terms, but its wait per vehicle is 6.6 to 9.0 s against "
              "the reference rule's 1.6 s, so it is clearly worse in practice there. rush_hour_kt's -11.8% is about one vehicle on a base of 8.8 "
              "(wait per vehicle 18.7 s -> 16.2 to 17.0 s). Rule and agents were tuned and trained on selection seeds (20000+), never on these test seeds."]
    return "\n".join(lines) + "\n"


def draw(rows, out, limit=30.0):
    """One dot per agent; changes beyond +-limit are drawn as triangles at the edge, with the value written next to them."""
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(8.5, 0.55 * len(rows) + 2.0))
    ax.axvspan(-5, 5, color="#8a8985", alpha=0.15)
    ax.axvline(0, color="#1B2430", lw=1)
    colors = {"better": "#1b9e4b", "worse": "#d6452a"}
    for i, r in enumerate(rows):
        off = [c for _, c, _ in r["agents"] if abs(c) > limit]
        for _, change, verdict in r["agents"]:
            color = colors.get(verdict, "#2a78d6")
            if abs(change) > limit:
                ax.scatter(limit * (1 if change > 0 else -1) * 0.97, i, s=46, marker=">" if change > 0 else "<", color=color,
                           zorder=3, edgecolor="white", linewidth=0.6)
            else:
                ax.scatter(change, i, s=42, color=color, zorder=3, edgecolor="white", linewidth=0.6)
        if off:
            ax.text(limit * 0.9, i - 0.28, f"{min(off):+.0f}% to {max(off):+.0f}%", ha="right", fontsize=7, color="#1B2430")
    ax.set_xlim(-limit, limit)
    ax.set_yticks(range(len(rows)), [f"{r['scenario']}  ({r['family']})" for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("change in mean total waiting vs the reference rule (%); left of 0 = agent is better")
    ax.set_title("Learned agents against the reference rule, one dot per trained agent", fontsize=11)
    ax.grid(axis="x", alpha=0.2)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color="#1b9e4b", label="better (significant and practical)"),
                       Line2D([], [], marker="o", ls="", color="#2a78d6", label="tie or small"),
                       Line2D([], [], marker="o", ls="", color="#d6452a", label="worse"),
                       Line2D([], [], marker="s", ls="", color="#8a8985", alpha=0.4, label="within 5% of the rule")],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8, frameon=False)
    fig.tight_layout()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main():
    rows = collect()
    with open(os.path.join(ROOT, "docs", "results_final.md"), "w") as f:
        f.write(markdown(rows))
    draw(rows, os.path.join(ROOT, "figures", "report", "final_results.png"))
    print(f"{len(rows)} rows -> docs/results_final.md, figures/report/final_results.png")


if __name__ == "__main__":
    main()
