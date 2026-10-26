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


def _net_connections():
    """(from edge, to edge) -> direction, read from the network the routes run on."""
    import xml.etree.ElementTree as ET

    root = ET.parse(os.path.join(ROOT, "configs", "intersection.net.xml")).getroot()
    return {(c.get("from"), c.get("to")): c.get("dir") for c in root.iter("connection") if c.get("tl")}


def test_turn_routes_follow_the_network_connections():
    conns = _net_connections()
    for rid, edges, base in gen.TURN_ROUTES:
        a, b = edges.split()
        assert conns[(a, b)] == ("r" if rid.endswith("_right") else "l"), rid
        assert a == dict(gen.ROUTES)[base].split()[0], f"{rid} must start on the same approach as {base}"


def test_turns_split_each_approach_rate_exactly():
    flows = gen.build_flows(Namespace(tidal=None, vehs_per_hour=1000, end=3600, period=900, turns=[0.2, 0.1], fleet=None))
    r = _rates(flows)
    assert len(flows) == 12
    assert r[("east_west", 0.0)] == 700 and r[("east_west_left", 0.0)] == 200 and r[("east_west_right", 0.0)] == 100
    for approach in ("east_west", "west_east", "north_south", "south_north"):
        assert sum(v for (rid, _), v in r.items() if rid.startswith(approach)) == 1000


def test_turns_keep_tidal_axis_logic():
    flows = gen.build_flows(Namespace(tidal=[1100, 300], vehs_per_hour=0, end=3600, period=900, turns=[0.15, 0.15], fleet="kathmandu"))
    r = _rates(flows)
    assert r[("north_south_left", 0.0)] == 165 and r[("east_west_left", 0.0)] == 45
    assert r[("east_west_left", 900.0)] == 165          # heavy axis flips with the turns


def test_invalid_turn_fractions_rejected():
    for bad in ([0.6, 0.4], [-0.1, 0.2]):
        try:
            gen.build_flows(Namespace(tidal=None, vehs_per_hour=100, end=100, period=900, turns=bad, fleet=None))
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


def test_fleet_shares_sum_to_one_and_types_are_used():
    assert abs(sum(p for _, p, _ in gen.FLEET) - 1.0) < 1e-9
    ns = Namespace(tidal=None, vehs_per_hour=900, end=3600, period=900, turns=None, fleet="kathmandu")
    assert all('type="kt"' in f for f in gen.build_flows(ns))
    assert gen.build_types(ns).count("<vType ") == 4
    assert 'id="car"' in gen.build_types(Namespace(fleet=None))


def test_kathmandu_scenarios_load_and_match_generator():
    expect = {"rush_hour_kt": dict(vehs_per_hour=900, tidal=None), "low_traffic_kt": dict(vehs_per_hour=120, tidal=None),
              "kathmandu_peak": dict(vehs_per_hour=1100, tidal=None), "tidal_kt": dict(vehs_per_hour=0, tidal=[1100, 300])}
    for name, kw in expect.items():
        scen = load_scenario(os.path.join(ROOT, "configs", "scenarios", f"{name}.yaml"))
        text = open(scen["route_file"]).read()
        flows = [l for l in text.splitlines() if "<flow" in l]
        want = gen.build_flows(Namespace(end=3600, period=900, turns=[0.15, 0.15], fleet="kathmandu", **kw))
        assert _rates(flows) == _rates(want), name
        assert "vTypeDistribution" in text and 'id="north_south_left"' in text, name


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
