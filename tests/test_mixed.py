"""Mixed-scenario training tests: scenario cycling, pinned evaluation,
aggregation maths, and reward settings in the sweep grid. No SUMO needed."""

import csv
import math
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl.agent import evaluate  # noqa: E402
from traffic_drl.agent.training import _aggregate  # noqa: E402
from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import traci_env  # noqa: E402
from traffic_drl.sweep import run_sweep  # noqa: E402
from test_state_reward import FakeTraci  # noqa: E402

CFG = os.path.join(ROOT, "configs", "dqn_mixed.yaml")


def _route(fake):
    return os.path.basename(fake.cmd[fake.cmd.index("--route-files") + 1])


class Stub:  # always action 0
    def act(self, s, greedy=False): return 0


def _env():
    fake = FakeTraci()
    traci_env.traci = fake
    return traci_env.TraciEnv(CFG), fake


def test_mixed_config_lists_three_scenarios():
    cfg = load_config(CFG)
    assert [os.path.basename(p) for p in cfg["scenarios"]] == ["low_traffic.yaml", "rush_hour.yaml", "tidal.yaml"]
    assert all(os.path.isabs(p) and os.path.exists(p) for p in cfg["scenarios"])
    env, _ = _env()
    assert env.scenario_names == ["low_traffic", "rush_hour", "tidal"]


def test_training_episodes_cycle_through_scenarios():
    env, fake = _env()
    seen = []
    for _ in range(4):
        env.reset()
        seen.append(_route(fake))
    assert seen == ["low_traffic.rou.xml", "rush_hour.rou.xml", "tidal.rou.xml", "low_traffic.rou.xml"]


def test_explicit_scenario_overrides_config_and_commas_make_a_mix():
    fake = FakeTraci()
    traci_env.traci = fake
    one = os.path.join(ROOT, "configs", "scenarios", "tidal.yaml")
    env = traci_env.TraciEnv(CFG, scenario=one)
    assert env.scenario_names == ["tidal"]
    two = traci_env.TraciEnv(CFG, scenario=f"{one},{os.path.join(ROOT, 'configs', 'scenarios', 'rush_hour.yaml')}")
    assert two.scenario_names == ["tidal", "rush_hour"]


def test_evaluate_pins_each_scenario_without_disturbing_the_training_cycle():
    env, fake = _env()
    env.reset()                                   # training episode 1 -> low_traffic
    result = evaluate(env, Stub(), episodes=1, max_steps=2)
    assert env.force_scenario is None
    for name in ("low_traffic", "rush_hour", "tidal"):
        assert f"{name}/mean_total_waiting" in result
    env.reset()                                   # training continues: episode 2 -> rush_hour
    assert _route(fake) == "rush_hour.rou.xml"


def test_oversampled_scenario_is_cycled_twice_but_evaluated_once():
    fake = FakeTraci()
    traci_env.traci = fake
    env = traci_env.TraciEnv(os.path.join(ROOT, "configs", "dqn_mixed_rush2.yaml"))
    seen = []
    for _ in range(4):
        env.reset()
        seen.append(_route(fake))
    assert seen == ["low_traffic.rou.xml", "rush_hour.rou.xml", "tidal.rou.xml", "rush_hour.rou.xml"]
    calls, orig = [], fake.start

    def record(cmd):
        calls.append(os.path.basename(cmd[cmd.index("--route-files") + 1]))
        orig(cmd)
    fake.start = record
    evaluate(env, Stub(), episodes=1, max_steps=2)
    assert sorted(calls) == ["low_traffic.rou.xml", "rush_hour.rou.xml", "tidal.rou.xml"]   # rush hour once, not twice


def test_aggregation_uses_log_scale_for_waiting_and_means_elsewhere():
    agg = _aggregate({
        "low": {"mean_total_waiting": 1.5, "throughput_per_hour": 400.0, "switches": 4.0},
        "rush": {"mean_total_waiting": 140.0, "throughput_per_hour": 3000.0, "switches": 40.0},
    })
    assert math.isclose(agg["mean_total_waiting"], math.expm1((math.log1p(1.5) + math.log1p(140.0)) / 2))
    assert agg["throughput_per_hour"] == 1700.0 and agg["switches"] == 22.0
    assert agg["low/mean_total_waiting"] == 1.5 and agg["rush/switches"] == 40.0
    # a relative blow-up in light traffic costs about as much as in heavy traffic
    light_bad = _aggregate({"a": {"mean_total_waiting": 25.0}, "b": {"mean_total_waiting": 140.0}})
    heavy_bad = _aggregate({"a": {"mean_total_waiting": 1.5}, "b": {"mean_total_waiting": 140.0 * 17}})
    assert light_bad["mean_total_waiting"] < heavy_bad["mean_total_waiting"]
    ok = _aggregate({"a": {"mean_total_waiting": 1.5}, "b": {"mean_total_waiting": 140.0}})
    assert light_bad["mean_total_waiting"] > ok["mean_total_waiting"]


def test_sweep_applies_reward_settings_per_run_and_restores_them():
    env, fake = _env()
    seen = []
    original_reset = env.reset

    def spying_reset():
        seen.append(env.reward_cfg["switch_penalty"])
        return original_reset()

    env.reset = spying_reset
    base_penalty = env.reward_cfg["switch_penalty"]
    cfg = {"dqn": {"hidden_sizes": [8], "learn_start": 100, "batch_size": 16}}
    with tempfile.TemporaryDirectory() as d:
        run_sweep(env, cfg, {"learning_rate": [0.001], "reward.switch_penalty": [0.0, 9.0]}, seeds=[0],
                  episodes=1, out_dir=d, eval_every=1, eval_episodes=1, final_eval_episodes=1, verbose=False)
        runs = list(csv.DictReader(open(os.path.join(d, "sweep_runs.csv"))))
        summary = list(csv.DictReader(open(os.path.join(d, "sweep_summary.csv"))))
    assert {r["reward.switch_penalty"] for r in runs} == {"0.0", "9.0"}
    assert 0.0 in seen and 9.0 in seen
    assert env.reward_cfg["switch_penalty"] == base_penalty          # restored afterwards
    assert any(k.endswith("/mean_total_waiting_mean") for k in summary[0])   # per-scenario columns kept


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
