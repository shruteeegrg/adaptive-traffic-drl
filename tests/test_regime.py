"""Regime-map grid and plot tests (no SUMO needed)."""

import csv
import importlib.util
import os
import re
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from traffic_drl.config import load_scenario  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


grid, plot = _load("make_regime_grid"), _load("plot_regime_map")


def test_axis_rates_keep_the_mean_and_the_ratio():
    for d in grid.DEMANDS:
        for r in grid.RATIOS:
            ns, ew = grid.axis_rates(d, r)
            assert abs((ns + ew) / 2 - d) <= 10, (d, r)          # rounding to 10 veh/h
            assert abs(ns / ew - r) / r < 0.15, (d, r, ns, ew)
    assert grid.axis_rates(400, 1) == (400, 400)


def test_committed_grid_matches_generator_and_loads():
    with tempfile.TemporaryDirectory() as tmp:
        names = grid.write_grid(tmp)
        assert len(names) == len(grid.DEMANDS) * len(grid.RATIOS)
        for n in names:
            for ext in (".rou.xml", ".yaml"):
                assert open(os.path.join(tmp, n + ext)).read() == open(os.path.join(ROOT, "configs", "scenarios", "grid", n + ext)).read(), n + ext
    sc = load_scenario(os.path.join(ROOT, "configs", "scenarios", "grid", "grid_d600_r4.yaml"))
    text = open(sc["route_file"]).read()
    rates = {m.group(1): float(m.group(2)) for m in re.finditer(r'route="(\w+)"[^>]*vehsPerHour="([\d.]+)"', text)}
    assert rates["north_south"] == rates["south_north"] == 960 and rates["east_west"] == rates["west_east"] == 240
    assert text.count("<flow") == 4          # static demand: one flow per approach, no flipping


def test_plot_reads_a_compare_summary_and_draws():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "compare_summary.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["scenario", "controller", "mean", "change_pct", "verdict"])
            w.writeheader()
            for d in (200, 400):
                for r in (1, 4):
                    w.writerow(dict(scenario=f"grid_d{d}_r{r}", controller="fixed", mean=10, change_pct=0, verdict="reference"))
                    w.writerow(dict(scenario=f"grid_d{d}_r{r}", controller="rule", mean=8, change_pct=-20 if r == 4 else -2, verdict="better"))
            w.writerow(dict(scenario="tidal", controller="rule", mean=7, change_pct=-94, verdict="better"))   # not a grid cell: ignored
        cells = plot.load_cells(path, "rule")
        assert set(cells) == {(200, 1), (200, 4), (400, 1), (400, 4)} and cells[(400, 4)][0] == -20
        out = os.path.join(tmp, "map.png")
        plot.draw(cells, "test", out)
        assert os.path.getsize(out) > 5000


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
