#!/usr/bin/env python3
"""Draw the regime map from a `traffic-drl compare` summary over the grid scenarios.

    python scripts/plot_regime_map.py --summary results/comparisons/grid/compare_summary.csv \
        --controller rule --reference fixed --out figures/report/regime_map.png

Each cell shows the percentage change in mean total waiting of --controller against --reference
(negative = better), annotated with the compare verdict. Rows are demand, columns unevenness.
"""
import argparse
import csv
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CELL = re.compile(r"grid_d(\d+)_r(\d+)")


def load_cells(summary_path: str, controller: str) -> dict:
    """{(demand, ratio): (change_pct, verdict, ref_mean, mean)} for one controller."""
    rows = list(csv.DictReader(open(summary_path)))
    out = {}
    for r in rows:
        m = CELL.fullmatch(r["scenario"])
        if m and r["controller"] == controller:
            out[(int(m.group(1)), int(m.group(2)))] = (float(r["change_pct"]), r["verdict"], float(r["mean"]))
    return out


def draw(cells: dict, title: str, out: str) -> None:
    demands = sorted({d for d, _ in cells})
    ratios = sorted({r for _, r in cells})
    fig, ax = plt.subplots(figsize=(1.6 * len(ratios) + 2.4, 1.1 * len(demands) + 1.8))
    vmax = max(30.0, max(abs(c[0]) for c in cells.values()))
    grid = [[cells.get((d, r), (float("nan"),))[0] for r in ratios] for d in demands]
    im = ax.imshow(grid, cmap="RdYlGn_r", vmin=-vmax, vmax=vmax, aspect="auto")
    for i, d in enumerate(demands):
        for j, r in enumerate(ratios):
            if (d, r) in cells:
                change, verdict, mean = cells[(d, r)]
                ax.text(j, i, f"{change:+.0f}%\n{verdict}", ha="center", va="center", fontsize=9, color="#1B2430")
    ax.set_xticks(range(len(ratios)), [f"{r}:1" if r > 1 else "even" for r in ratios])
    ax.set_yticks(range(len(demands)), [f"{d}" for d in demands])
    ax.set_xlabel("NS : EW demand ratio")
    ax.set_ylabel("mean demand (veh/h per approach)")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="change in mean total waiting (%)")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--summary", required=True)
    p.add_argument("--controller", default="rule")
    p.add_argument("--reference", default="fixed")
    p.add_argument("--out", default="figures/report/regime_map.png")
    a = p.parse_args()
    cells = load_cells(a.summary, a.controller)
    if not cells:
        raise SystemExit(f"no grid cells for controller '{a.controller}' in {a.summary}")
    draw(cells, f"{a.controller} vs {a.reference}: where adaptive control helps", a.out)
    print(f"wrote {a.out} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
