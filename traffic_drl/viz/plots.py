"""Plotting from saved logs -- the single implementation behind the CLI's
`plot` command, the saved report figures and (later) the live demo app.

Two chart forms, picked by the data's job:
  plot_training    -- change over time: training/evaluation curves from a
                      training log CSV (written by traffic_drl.agent.training)
                      and an optional evaluation-history CSV (sweep `_evals.csv`).
  plot_comparison  -- magnitude across controllers: mean +- spread over
                      episodes for each scenario, one panel per metric.

Colour follows the entity, not its rank: the fixed-time baseline is always
neutral gray (context); learned controllers take the validated categorical
slots in fixed order (blue, then orange, then aqua). Marks are thin, the grid
is recessive, text uses ink colours (never the series colour), and every
comparison has a text table view (`comparison_table`) so no information is
carried by colour alone.
"""

import csv
import math

import matplotlib

matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
BASELINE_GRAY = "#8a8985"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]   # categorical slots 1-3 (validated, fixed order)

METRICS = {
    # key: (title, direction hint)
    "reward": ("Episode reward", "higher is better"),
    "mean_total_waiting": ("Vehicles waiting (queue + backlog)", "lower is better"),
    "mean_queue": ("Queue on approach edges", "lower is better"),
    "mean_backlog": ("Backlog outside network", "lower is better"),
    "avg_wait_per_vehicle": ("Average wait per vehicle (s)", "lower is better"),
    "throughput_per_hour": ("Throughput (vehicles/hour)", "higher is better"),
    "switches": ("Phase switches per episode", "context"),
}
TRAINING_PANELS = ("reward", "mean_total_waiting", "throughput_per_hour", "switches")
COMPARE_DEFAULT = ("mean_total_waiting", "throughput_per_hour", "switches")


def read_csv(path: str) -> list:
    """Rows as dicts of floats; empty cells become None."""
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append({k: (float(v) if v not in ("", None) else None) for k, v in row.items()
                         if k != "checkpoint"})
    return rows


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8)


def _title(ax, key):
    name, hint = METRICS.get(key, (key, ""))
    ax.set_title(name, loc="left", fontsize=10, color=INK)
    if hint:
        ax.text(1.0, 1.02, hint, transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color=INK_2)


def _series(rows, key):
    pts = [(r["episode"], r[key]) for r in rows if r.get(key) is not None]
    return [p[0] for p in pts], [p[1] for p in pts]


def plot_reward_curve(log_path: str, out_path: str, window: int = 5) -> str:
    """Reward-only curve (works for Q-table logs, which have no metrics)."""
    rows = read_csv(log_path)
    return plot_training(log_path, out_path, panels=("reward",), window=window, _rows=rows)


def plot_training(log_path: str, out_path: str, evals_path: str = None, window: int = 5,
                  panels=TRAINING_PANELS, title: str = None, _rows=None) -> str:
    """Training curves (blue: smoothed mean over `window` episodes with the raw
    episodes faint behind it) and, if given, greedy evaluations on unseen seeds
    (orange markers). Only panels with data are drawn."""
    train = _rows if _rows is not None else read_csv(log_path)
    evals = read_csv(evals_path) if evals_path else []
    draw = [k for k in panels if _series(train, k)[0] or _series(evals, k)[0]]
    if not draw:
        raise ValueError("no plottable metrics in the log")

    ncols = 1 if len(draw) == 1 else 2
    nrows = math.ceil(len(draw) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.8 * ncols / (1 if ncols == 1 else 1.15), 3.2 * nrows),
                             squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    flat = [ax for row in axes for ax in row]

    for ax, key in zip(flat, draw):
        _style(ax)
        _title(ax, key)
        x, y = _series(train, key)
        if x:
            ax.plot(x, y, color=SERIES[0], alpha=0.25, linewidth=1.0)
            if len(y) >= window:
                avg = [sum(y[i - window + 1:i + 1]) / window for i in range(window - 1, len(y))]
                ax.plot(x[window - 1:], avg, color=SERIES[0], linewidth=2.0, label=f"training ({window}-episode mean)")
            else:
                ax.plot(x, y, color=SERIES[0], linewidth=2.0, label="training")
        ex, ey = _series(evals, key)
        if ex:
            ax.plot(ex, ey, color=SERIES[1], linewidth=2.0, marker="o", markersize=6,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, label="evaluation (greedy, unseen seeds)")
        ax.set_xlabel("episode", fontsize=8, color=INK_2)
        ax.legend(frameon=False, fontsize=7.5, labelcolor=INK_2, loc="best")
    for ax in flat[len(draw):]:
        ax.axis("off")
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def _is_baseline(label: str) -> bool:
    return label.lower().startswith(("fixed", "baseline", "timer"))


def label_colors(labels) -> dict:
    """Baseline -> neutral gray; everything else -> categorical slots in the
    order the labels are given. Stable for a given label order."""
    colors, slot = {}, 0
    for label in labels:
        if _is_baseline(label):
            colors[label] = BASELINE_GRAY
        else:
            colors[label] = SERIES[min(slot, len(SERIES) - 1)]
            slot += 1
    return colors


def _stats(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return None, None, []
    mean = sum(vals) / len(vals)
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
    return mean, std, vals


def plot_comparison(results: dict, out_path: str, metrics=COMPARE_DEFAULT, title: str = None) -> str:
    """Grouped bars: x = scenario, one bar per controller, one panel per
    metric. Bar = mean over episodes, whisker = standard deviation, dots =
    individual episodes. `results` is {scenario: {controller: [episode dicts]}}."""
    groups = list(results)
    labels = []
    for g in groups:
        for lab in results[g]:
            if lab not in labels:
                labels.append(lab)
    # baseline first, so the learned controllers read against it
    labels.sort(key=lambda lab: 0 if _is_baseline(lab) else 1)
    colors = label_colors(labels)

    fig, axes = plt.subplots(1, len(metrics), figsize=(4.6 * len(metrics), 3.8), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    width = 0.8 / len(labels)
    for ax, key in zip(axes[0], metrics):
        _style(ax)
        _title(ax, key)
        for li, lab in enumerate(labels):
            xs, means, stds, dots = [], [], [], []
            for gi, g in enumerate(groups):
                mean, std, vals = _stats(results[g].get(lab, []), key)
                if mean is None:
                    continue
                x = gi + (li - (len(labels) - 1) / 2) * width
                xs.append(x); means.append(mean); stds.append(std); dots.append((x, vals))
            ax.bar(xs, means, width=width * 0.85, color=colors[lab], edgecolor=SURFACE, linewidth=1.5,
                   label=lab, zorder=2)
            ax.errorbar(xs, means, yerr=stds, fmt="none", ecolor=INK_2, elinewidth=1.0, capsize=2.5, zorder=3)
            for x, vals in dots:
                ax.scatter([x] * len(vals), vals, s=9, color=INK_2, alpha=0.35, zorder=4, linewidths=0)
            for x, m, sd, (_, vals) in zip(xs, means, stds, dots):
                # label sits above the whisker and the episode dots, never on them
                y_top = max(m + sd, max(vals))
                ax.annotate(f"{m:.0f}" if abs(m) >= 100 else f"{m:.1f}", (x, y_top), textcoords="offset points",
                            xytext=(0, 4), ha="center", fontsize=7.5, color=INK)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels(groups, fontsize=8, color=INK_2)
        ax.axhline(0, color=GRID, linewidth=0.8)
    handles, names = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=len(names), frameon=False, fontsize=8.5,
               labelcolor=INK)
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95 if title else 1))
    fig.savefig(out_path, dpi=140, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def comparison_table(results: dict, metrics=COMPARE_DEFAULT) -> str:
    """The same numbers as the comparison chart, as text (mean +- std, n):
    the non-visual view of the chart."""
    lines = []
    for g, by_label in results.items():
        lines.append(f"[{g}]")
        for lab, rows in by_label.items():
            cells = []
            for key in metrics:
                mean, std, vals = _stats(rows, key)
                if mean is not None:
                    cells.append(f"{key}={mean:.1f}±{std:.1f}")
            lines.append(f"  {lab:<16} n={len(rows):<3} " + "  ".join(cells))
    return "\n".join(lines)
