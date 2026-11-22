"""Junction intake: spec validation, generated route files, and (with SUMO) that the result actually runs."""
import os
import xml.etree.ElementTree as ET

import pytest
import yaml

from traffic_drl import intake
from traffic_drl.config import load_scenario

BASE = {"name": "t", "demand": {"east": 300, "north": 600, "west": 300, "south": 600}}


def _flows(res):
    return ET.parse(res["route_file"]).getroot().findall("flow")


def test_constant_demand_writes_one_flow_per_approach(tmp_path):
    res = intake.build_scenario(BASE, tmp_path)
    flows = _flows(res)
    assert len(flows) == 4
    assert {f.get("route"): float(f.get("vehsPerHour")) for f in flows} == {
        "east_west": 300, "west_east": 300, "north_south": 600, "south_north": 600}
    assert all(f.get("end") == "1800" for f in flows)          # 30 minutes by default
    assert res["summary"]["vehicles"] == pytest.approx(900)    # 1800 veh/h in total x 0.5 h


def test_scenario_yaml_loads_like_the_shipped_ones(tmp_path):
    res = intake.build_scenario(BASE, tmp_path)
    sc = load_scenario(res["scenario_yaml"])
    assert sc["name"] == "t" and os.path.exists(sc["route_file"])


def test_periods_are_consecutive_and_zero_rates_skipped(tmp_path):
    spec = {"name": "p", "demand": [{"minutes": 10, "north": 500}, {"minutes": 5, "east": 400}]}
    flows = _flows(intake.build_scenario(spec, tmp_path))
    assert [(f.get("route"), f.get("begin"), f.get("end")) for f in flows] == [
        ("north_south", "0", "600"), ("east_west", "600", "900")]


def test_turns_split_the_rate_and_add_routes(tmp_path):
    res = intake.build_scenario({**BASE, "turns": {"left": 0.1, "right": 0.2}}, tmp_path)
    rates = {f.get("route"): float(f.get("vehsPerHour")) for f in _flows(res)}
    assert rates["north_south"] == pytest.approx(420) and rates["north_south_left"] == pytest.approx(60)
    assert rates["north_south_right"] == pytest.approx(120)
    ids = {r.get("id") for r in ET.parse(res["route_file"]).getroot().findall("route")}
    assert {"north_south_left", "east_west_right"} <= ids


def test_vehicle_mix_options(tmp_path):
    root = lambda spec: ET.parse(intake.build_scenario(spec, tmp_path)["route_file"]).getroot()  # noqa: E731
    assert root(BASE).find("vType").get("id") == "car"
    probs = [float(v.get("probability")) for v in root({**BASE, "vehicle_mix": "mixed"}).iter("vType")]
    assert sum(probs) == pytest.approx(1.0)
    shares = {v.get("id"): float(v.get("probability")) for v in root({**BASE, "vehicle_mix": {"car": 0.75, "bus": 0.25}}).iter("vType")}
    assert shares == {"car": pytest.approx(0.75), "bus": pytest.approx(0.25)}


@pytest.mark.parametrize("bad, text", [
    ({"name": "a b", "demand": BASE["demand"]}, "name"),
    ({"name": "t"}, "demand"),
    ({"name": "t", "demand": {"east": -5}}, "outside"),
    ({"name": "t", "demand": {"up": 5}}, "unknown keys"),
    ({"name": "t", "demand": {"east": "lots"}}, "number"),
    ({"name": "t", "demand": [{"east": 5}]}, "minutes"),
    ({**BASE, "vehicle_mix": {"car": 0.5, "bus": 0.2}}, "add up to 1"),
    ({**BASE, "vehicle_mix": {"tuk": 1.0}}, "unknown types"),
    ({**BASE, "turns": {"left": 0.6, "right": 0.5}}, "less than 1"),
    ({**BASE, "extra": 1}, "unknown top-level"),
])
def test_bad_specs_are_rejected_with_a_reason(tmp_path, bad, text):
    with pytest.raises(intake.SpecError, match=text):
        intake.build_scenario(bad, tmp_path)


def test_advisories_flag_capacity(tmp_path):
    heavy = intake.build_scenario({"name": "h", "demand": {"east": 1200, "north": 1200, "west": 1200, "south": 1200}}, tmp_path)
    assert heavy["summary"]["peak_load"] > 1.0 and "exceeds" in heavy["advisories"][0]
    light = intake.build_scenario({"name": "l", "demand": {"east": 50, "north": 50, "west": 50, "south": 50}}, tmp_path)
    assert "very light" in light["advisories"][0]
    assert intake.build_scenario(BASE, tmp_path)["advisories"] == []


def test_example_spec_builds(tmp_path):
    root = os.path.join(os.path.dirname(__file__), "..")
    res = intake.build_from_file(os.path.join(root, "configs", "examples", "junction_example.yaml"), tmp_path)
    assert res["summary"]["minutes"] == 30


def test_generated_scenario_runs_in_sumo(tmp_path):
    pytest.importorskip("traci")
    from traffic_drl.env import TraciEnv

    spec = {**BASE, "name": "sim", "vehicle_mix": "mixed", "turns": {"left": 0.1, "right": 0.1}}
    res = intake.build_scenario(spec, tmp_path)
    cfg = os.path.join(os.path.dirname(__file__), "..", "configs", "dqn_v_dqfd.yaml")
    env = TraciEnv(cfg, scenario=res["scenario_yaml"])
    env.reset()
    for i in range(60):
        env.step(i // 15 % 2)
    m = env.metrics()
    env.close()
    assert m["arrived"] > 0
