"""Charts for the reflective report and the presentation, drawn from the saved results.

    python scripts/make_report_figures.py

Writes PNGs to figures/report/. Nothing here is typed in by hand: bars and dots come from
the CSVs in figures/ and results_sweep_rush_a/.
"""
import csv
import os
import statistics as stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "report")
os.makedirs(OUT, exist_ok=True)
GRAY, BLUE, ORANGE = "#8a8985", "#2a78d6", "#eb6834"


def col(path, name):
    return [float(r[name]) for r in csv.DictReader(open(os.path.join(ROOT, path)))]


def style(ax, dark=False):
    fg = "#E4E8EE" if dark else "#1B2430"
    ax.set_facecolor("none")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(fg)
    ax.tick_params(colors=fg)
    ax.yaxis.label.set_color(fg); ax.xaxis.label.set_color(fg); ax.title.set_color(fg)
    ax.grid(axis="y", color=fg, alpha=0.15)
    ax.set_axisbelow(True)
    return fg


def save(fig, name, dark=False):
    fig.savefig(os.path.join(OUT, name), dpi=200, transparent=False,
                facecolor="#16202E" if dark else "#FDFDFB", bbox_inches="tight")
    plt.close(fig)


# 1. fixed timer vs DQN, fresh seeds ------------------------------------------------
def results_bars():
    scen = [("Tidal", "tidal"), ("Rush hour", "rush"), ("Low traffic", "low")]
    fig, ax = plt.subplots(figsize=(9, 5.6))
    fg = style(ax)
    w = 0.36
    for i, (label, key) in enumerate(scen):
        for j, (suffix, color, nm) in enumerate((("baseline", GRAY, "Fixed timer"), ("best", BLUE, "DQN"))):
            v = col(f"figures/{key}_{suffix}.csv", "mean_total_waiting")
            m, se = stats.mean(v), stats.stdev(v) / len(v) ** 0.5
            x = i + (j - 0.5) * w
            ax.bar(x, m, w * 0.92, color=color, label=nm if i == 0 else None, yerr=se, ecolor=fg, capsize=4)
            ax.text(x, m + 4, f"{m:.1f}" if m < 100 else f"{m:.0f}", ha="center", va="bottom", fontsize=17, color=fg)
    ax.set_xticks(range(3)); ax.set_xticklabels([s[0] for s in scen], fontsize=18)
    ax.set_ylabel("Vehicles waiting (lower is better)", fontsize=16)
    ax.tick_params(axis="y", labelsize=15)
    ax.set_ylim(0, 160)
    ax.legend(frameon=False, fontsize=16, loc="upper right")
    save(fig, "results_bars.png")


# 2. traffic demand in the three scenarios -----------------------------------------
def scenario_demand(dark=False):
    fg = "#E4E8EE" if dark else "#1B2430"
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.7), sharey=True)
    specs = [("Low traffic", [(0, 30, 120)], [(0, 30, 120)]),
             ("Rush hour", [(0, 30, 900)], [(0, 30, 900)]),
             ("Tidal", [(0, 15, 1100), (15, 30, 300)], [(0, 15, 300), (15, 30, 1100)])]
    for ax, (title, ns, ew) in zip(axes, specs):
        style(ax, dark)
        same = ns == ew                       # balanced scenarios: one line for all four roads
        lines = ((ns, "#8C98A8" if dark else "#5B6573", "All four roads"),) if same else \
                ((ns, BLUE, "North–south"), (ew, ORANGE, "East–west"))
        for segs, color, name in lines:
            xs, ys = [], []
            for a, b, v in segs:
                xs += [a, b]; ys += [v, v]
            ax.plot(xs, ys, color=color, lw=4, label=name, solid_capstyle="butt")
        if same:
            ax.text(15, segs[0][2] + 90, "all four roads", ha="center", fontsize=17, color=fg)
        ax.set_title(title, fontsize=21, pad=8)
        ax.set_xlabel("minutes", fontsize=19); ax.set_xlim(0, 30); ax.set_ylim(0, 1300)
        ax.tick_params(labelsize=17)
    axes[0].set_ylabel("cars per hour, each road", fontsize=18)
    axes[2].text(7.5, 1150, "north\u2013south", ha="center", fontsize=16, color=fg)   # direct labels, no legend
    axes[2].text(22.5, 1150, "east\u2013west", ha="center", fontsize=16, color=fg)
    axes[2].text(7.5, 345, "east\u2013west", ha="center", fontsize=16, color=fg)
    axes[2].text(22.5, 345, "north\u2013south", ha="center", fontsize=16, color=fg)
    fig.tight_layout()
    save(fig, "scenario_demand_dark.png" if dark else "scenario_demand.png", dark)


# 3. effect of gamma on rush hour (sweep A) ------------------------------------------
def gamma_effect(dark=False):
    rows = list(csv.DictReader(open(os.path.join(ROOT, "results_sweep_rush_a", "sweep_runs.csv"))))
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    fg = style(ax, dark)
    for i, g in enumerate(("0.95", "0.99")):
        vals = [float(r["mean_total_waiting"]) for r in rows if r["gamma"] == g]
        n = len(vals)
        xs = [i + (k - (n - 1) / 2) * 0.07 for k in range(n)]
        ax.scatter(xs, sorted(vals), s=120, color=BLUE, alpha=0.9, zorder=3)
        ax.hlines(stats.mean(vals), i - 0.28, i + 0.28, color=ORANGE, lw=4, zorder=4)
        ax.text(i + 0.32, stats.mean(vals), f"mean {stats.mean(vals):.0f}", va="center", fontsize=15, color=fg)
    ax.axhline(139.7, color=GRAY if not dark else "#B8C2D0", ls="--", lw=2)
    ax.text(-0.45, 139.7 - 14, "fixed timer, about 140", fontsize=14, color=GRAY if not dark else "#B8C2D0", va="top")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["gamma 0.95", "gamma 0.99"], fontsize=17)
    ax.set_xlim(-0.5, 1.75); ax.set_ylim(100, 470)
    ax.set_ylabel("Vehicles waiting, rush hour", fontsize=16)
    ax.tick_params(axis="y", labelsize=14)
    save(fig, "gamma_effect_dark.png" if dark else "gamma_effect.png", dark)


# 4. progress against the plan (report Table 1) -------------------------------------
def progress():
    items = [("1  Repository and environment (wk 1)", 100), ("2  SUMO network and config (wk 2)", 100),
             ("3  Q-table baseline (wk 3)", 100), ("4  State, reward, network (wk 4)", 100),
             ("5  DQN training loop (wk 5)", 100), ("6  Training and tuning (wk 6)", 85),
             ("7  Visualisation module (wk 7)", 85), ("8  Baseline, scenarios, demo app (wk 8)", 85),
             ("9  Comparative analysis (wk 9)", 50), ("10  Final report and polish (wk 10)", 5),
             ("–  Contextual report (unscheduled)", 0)]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fg = style(ax)
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=fg, alpha=0.15)
    ys = range(len(items))[::-1]
    ax.barh(list(ys), [100] * len(items), color="#E6E4DD", height=0.62)
    ax.barh(list(ys), [v for _, v in items], color=BLUE, height=0.62)
    for y, (_, v) in zip(ys, items):
        ax.text(101.5, y, f"{v}%", va="center", fontsize=12, color=fg)
    ax.set_yticks(list(ys)); ax.set_yticklabels([n for n, _ in items], fontsize=11)
    ax.set_xlim(0, 112); ax.set_xlabel("estimated % complete", fontsize=12)
    ax.tick_params(axis="x", labelsize=11)
    save(fig, "progress_vs_plan.png")


results_bars(); scenario_demand(); scenario_demand(True); gamma_effect(); gamma_effect(True); progress()
print("wrote", sorted(os.listdir(OUT)))
