"""Plotting tests: files are written, data handling is right, and the colour
rules hold (baseline gray, fixed categorical order). No SUMO needed."""

import csv
import io
import contextlib
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl import cli, viz  # noqa: E402
from traffic_drl.viz import plots  # noqa: E402
from traffic_drl.env import traci_env  # noqa: E402
from test_state_reward import FakeTraci  # noqa: E402

FULL_COLS = ["episode", "reward", "epsilon", "loss", "mean_queue", "mean_backlog", "mean_total_waiting",
             "avg_wait_per_vehicle", "throughput_per_hour", "switches", "ns_green_fraction"]


def _write(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def _full_log(path, n=12):
    _write(path, FULL_COLS, [[i, -1500 + 10 * i, 0.5, "" if i == 1 else 1.0, 15, 100, 250 - i, 20, 2500 + i, 60 - i, 0.5]
                             for i in range(1, n + 1)])


def _is_png(path):
    return os.path.getsize(path) > 2000 and open(path, "rb").read(8) == b"\x89PNG\r\n\x1a\n"


def test_read_csv_turns_blanks_into_none_and_drops_checkpoint_names():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.csv")
        _write(p, ["checkpoint", "episode", "loss"], [["a_best.npz", 1, ""], ["b_best.npz", 2, 0.5]])
        rows = viz.read_csv(p)
    assert rows == [{"episode": 1.0, "loss": None}, {"episode": 2.0, "loss": 0.5}]


def test_plot_training_with_and_without_evals():
    with tempfile.TemporaryDirectory() as d:
        log, evals = os.path.join(d, "log.csv"), os.path.join(d, "evals.csv")
        _full_log(log)
        _write(evals, ["episode", "reward", "mean_total_waiting", "throughput_per_hour", "switches"],
               [[5, -1400, 200, 2600, 50], [10, -1350, 190, 2650, 45]])
        assert _is_png(viz.plot_training(log, os.path.join(d, "a.png")))
        assert _is_png(viz.plot_training(log, os.path.join(d, "b.png"), evals_path=evals, title="t"))


def test_reward_only_log_still_plots():
    with tempfile.TemporaryDirectory() as d:     # Q-table logs have no metric columns
        log = os.path.join(d, "q.csv")
        _write(log, ["episode", "reward", "epsilon", "loss"], [[i, -100 + i, 0.5, ""] for i in range(1, 9)])
        assert _is_png(viz.plot_reward_curve(log, os.path.join(d, "q.png")))


def test_log_with_nothing_to_plot_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "bad.csv")
        _write(log, ["episode", "epsilon"], [[1, 1.0]])
        try:
            viz.plot_training(log, os.path.join(d, "x.png"))
        except ValueError:
            return
    raise AssertionError("expected ValueError")


def test_baseline_is_gray_and_learned_controllers_take_slots_in_order():
    colors = viz.label_colors(["Fixed-time", "DQN", "Q-table"])
    assert colors["Fixed-time"] == plots.BASELINE_GRAY
    assert colors["DQN"] == plots.SERIES[0] and colors["Q-table"] == plots.SERIES[1]
    # colour follows the entity: dropping the baseline must not repaint DQN
    assert viz.label_colors(["DQN", "Q-table"])["DQN"] == plots.SERIES[0]


def test_comparison_chart_and_table():
    rows = lambda w, t: [{"reward": -1, "mean_total_waiting": w + i, "throughput_per_hour": t, "switches": 40}
                         for i in range(3)]
    results = {"rush_hour": {"DQN": rows(140, 3000), "Fixed-time": rows(138, 3020)},
               "tidal": {"Fixed-time": rows(110, 2440), "DQN": rows(30, 2620)}}
    with tempfile.TemporaryDirectory() as d:
        assert _is_png(viz.plot_comparison(results, os.path.join(d, "c.png"), title="t"))
    table = viz.comparison_table(results)
    assert "[tidal]" in table and "DQN" in table and "mean_total_waiting=31.0±1.0" in table


def test_evaluate_save_csv_then_plot_compare_roundtrip():
    traci_env.traci = FakeTraci()
    dqn_cfg = os.path.join(ROOT, "configs", "dqn.yaml")
    with tempfile.TemporaryDirectory() as d:
        base, out_png = os.path.join(d, "base.csv"), os.path.join(d, "cmp.png")
        with contextlib.redirect_stdout(io.StringIO()):
            assert cli.main(["baseline", "--config", dqn_cfg, "--episodes", "2", "--save-csv", base]) == 0
        rows = viz.read_csv(base)
        assert [r["episode"] for r in rows] == [1.0, 2.0] and "mean_total_waiting" in rows[0]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["plot", "compare", "--out", out_png, "--item", f"rush_hour:Fixed-time={base}",
                             "--item", f"rush_hour:Other={base}"])
        assert code == 0 and _is_png(out_png) and "[rush_hour]" in out.getvalue()


def test_bad_plot_item_is_rejected():
    try:
        cli.main(["plot", "compare", "--out", "x.png", "--item", "no-equals-sign"])
    except SystemExit as e:
        assert "SCENARIO:LABEL=CSV" in str(e)
        return
    raise AssertionError("expected SystemExit")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
