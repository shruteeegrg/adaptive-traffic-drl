"""Route generator / scenario tests (no SUMO needed)."""

import importlib.util
import os
import re
import sys
from argparse import Namespace

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from traffic_drl.config import load_scenario  # noqa: E402

spec = importlib.util.spec_from_file_location("generate_routes", os.path.join(ROOT, "scripts", "generate_routes.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def _rates(flows):
    out = {}
    for f in flows:
        rid = re.search(r'route="(\w+)"', f).group(1)
        begin = float(re.search(r'begin="([\d.]+)"', f).group(1))
        out[(rid, begin)] = float(re.search(r'vehsPerHour="([\d.]+)"', f).group(1))
    return out


def test_uniform_demand_unchanged():
    flows = gen.build_flows(Namespace(tidal=None, vehs_per_hour=900, end=3600, period=900))
    assert len(flows) == 4 and set(_rates(flows).values()) == {900.0}


def test_tidal_alternates_heavy_axis():
    flows = gen.build_flows(Namespace(tidal=[1100, 300], vehs_per_hour=0, end=3600, period=900))
    r = _rates(flows)
    assert len(flows) == 16
    assert r[("north_south", 0.0)] == r[("south_north", 0.0)] == 1100 and r[("east_west", 0.0)] == 300
    assert r[("east_west", 900.0)] == r[("west_east", 900.0)] == 1100 and r[("north_south", 900.0)] == 300
    assert r[("north_south", 1800.0)] == 1100  # swaps back


def test_tidal_scenario_file_loads_and_matches_generator():
    scen = load_scenario(os.path.join(ROOT, "configs", "scenarios", "tidal.yaml"))
    assert os.path.exists(scen["route_file"]) and scen["name"] == "tidal"
    flows = [l for l in open(scen["route_file"]) if "<flow" in l]
    expected = gen.build_flows(Namespace(tidal=[1100, 300], vehs_per_hour=0, end=3600, period=900))
    assert _rates(flows) == _rates(expected)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
