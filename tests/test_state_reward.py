"""Week 4 tests: config-driven state/reward design, config inheritance,
and TraciEnv wiring against a fake traci (no SUMO needed).
    python -m pytest tests/test_state_reward.py -v   (or: python tests/test_state_reward.py)
"""

import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import features  # noqa: E402
from traffic_drl.env import traci_env  # noqa: E402
from traffic_drl.agent import MLP  # noqa: E402

FULL = {"state": {"features": ["queue", "waiting_time", "phase", "phase_elapsed"],
                  "queue_scale": 10.0, "wait_scale": 100.0, "phase_elapsed_scale": 50.0}}


def test_default_state_and_reward_match_week2():
    cfg, rcfg = features.state_config({}), features.reward_config({})
    s = features.build_state(cfg, [3, 1, 0, 2], [9, 9, 9, 9], 1, 5, 2)
    assert s.tolist() == [3, 1, 0, 2]
    cost = features.accrue_cost(rcfg, queue_total=6, wait_total=36, backlog_total=50)
    assert cost == 6.0                                   # only queue counts by default
    assert features.compute_reward(rcfg, cost, True) == -6.0


def test_full_state_layout_and_scaling():
    cfg = features.state_config(FULL)
    s = features.build_state(cfg, [10, 0, 5, 0], [100, 0, 0, 50], 1, 25, 2)
    assert features.state_size(cfg, 4, 2) == len(s) == 11
    assert np.allclose(s, [1, 0, .5, 0, 1, 0, 0, .5, 0, 1, .5])


def test_unknown_feature_rejected():
    try:
        features.state_config({"state": {"features": ["queue", "speed"]}})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_reward_weights_and_switch_penalty():
    r = features.reward_config({"reward": {"queue_weight": 1, "wait_weight": 0.5, "backlog_weight": 2,
                                           "switch_penalty": 4, "reward_scale": 2}})
    cost = features.accrue_cost(r, queue_total=4, wait_total=10, backlog_total=3)
    assert cost == 4 + 5 + 6
    assert features.compute_reward(r, cost, False) == -15 / 2
    assert features.compute_reward(r, cost, True) == -(15 + 4) / 2


def test_config_extends_overrides_and_inherits():
    cfg = load_config(os.path.join(ROOT, "configs", "dqn.yaml"))
    assert cfg["name"] == "intersection_dqn"                       # overridden
    assert cfg["traffic_light_id"] == "A1"                         # inherited
    assert cfg["qtable"]["alpha"] == 0.1                           # inherited, nested
    assert os.path.isabs(cfg["sumocfg_file"]) and cfg["sumocfg_file"].endswith("intersection.sumocfg")
    assert "extends" not in cfg


def test_network_input_size_comes_from_config():
    cfg = load_config(os.path.join(ROOT, "configs", "dqn.yaml"))
    n_in = features.state_size(features.state_config(cfg), len(cfg["approaches"]), 2)
    net = MLP.from_config(cfg, n_in, 2)
    assert n_in == 11 and net.forward(np.zeros(n_in)).shape == (1, 2)


class FakeTraci:
    """Minimal traci stand-in: fixed queues/waits, counts simulated seconds."""
    def __init__(self):
        self.t = 0
        self.phases = []
        self.cmd = None
        self.trafficlight = self
        self.edge = self
        self.simulation = self

    def start(self, cmd): self.cmd = cmd
    def close(self): pass
    def simulationStep(self): self.t += 1
    def setPhase(self, tls, phase): self.phases.append(phase)
    def getLastStepHaltingNumber(self, e): return 4
    def getWaitingTime(self, e): return 20.0
    def getMinExpectedNumber(self): return 1
    def getPendingVehicles(self): return ('v1', 'v2', 'v3')
    def getArrivedNumber(self): return 1
    def getDepartedNumber(self): return 2


def _env(config_name, monkeypatch_fake):
    traci_env.traci = monkeypatch_fake
    return traci_env.TraciEnv(os.path.join(ROOT, "configs", config_name))


def test_traci_env_default_config_is_unchanged():
    fake = FakeTraci()
    env = _env("intersection.yaml", fake)
    s = env.reset()
    assert s.tolist() == [4, 4, 4, 4, 1, 0]       # 4 queues + one-hot NS phase (Week 6 default)
    s, r, done, _ = env.step(0)
    assert r == -16.0 and not done


def test_traci_env_full_state_tracks_phase_and_switch_penalty():
    fake = FakeTraci()
    env = _env("dqn.yaml", fake)
    assert env.decision_interval == 5
    s = env.reset()
    assert s.shape == (11,) == (env.state_size,)
    # cost per simulated second = queue 16 + 0.1 * 3 pending = 16.3; 5 s per decision
    s, r, _, _ = env.step(0)                       # stay on NS: no switch
    assert fake.t == 5
    assert s[8:10].tolist() == [1, 0] and np.isclose(s[10], 5 / 60)
    assert np.isclose(r, -(5 * 16.3) / 50)
    s, _, _, _ = env.step(0)
    assert np.isclose(s[10], 10 / 60)              # time-in-phase accumulates
    s, r, _, _ = env.step(1)                       # switch: 3 s yellow + 5 s green, all charged
    assert fake.t == 5 + 5 + 8
    assert s[8:10].tolist() == [0, 1] and np.isclose(s[10], 5 / 60)
    assert np.isclose(r, -(8 * 16.3 + 5) / 50)
    assert 3 in fake.phases                        # yellow inserted before the new green


def test_switching_is_charged_for_the_yellow_seconds_it_burns():
    """Regression guard for the Week 6 exploit: with reward charged per
    decision, flipping every step hid 3 s of congestion per flip."""
    def reward_of(policy):
        fake = FakeTraci()
        env = _env("intersection.yaml", fake)
        env.reset()
        total = 0.0
        while fake.t < 40:
            _, r, _, _ = env.step(policy(fake.t))
            total += r
        return total, fake.t

    hold, t_hold = reward_of(lambda t: 0)
    flip, t_flip = reward_of(lambda t: (t // 4) % 2)
    # Same simulated time, same queues every second => same cost. Per-decision
    # charging would have made `flip` look 4x cheaper.
    assert t_hold == t_flip == 40
    assert np.isclose(hold, flip)


def test_scenario_route_file_is_passed_to_sumo():
    fake = FakeTraci()
    traci_env.traci = fake
    scen = os.path.join(ROOT, "configs", "scenarios", "rush_hour.yaml")
    env = traci_env.TraciEnv(os.path.join(ROOT, "configs", "intersection.yaml"), scenario=scen)
    env.reset()
    i = fake.cmd.index("--route-files")
    assert fake.cmd[i + 1].endswith("rush_hour.rou.xml") and os.path.exists(fake.cmd[i + 1])


def test_no_scenario_leaves_sumo_command_unchanged():
    fake = FakeTraci()
    _env("intersection.yaml", fake).reset()
    assert "--route-files" not in fake.cmd


def test_bad_scenarios_rejected():
    import tempfile
    from traffic_drl.config import load_scenario
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "s.yaml")
        open(bad, "w").write("name: x\nroute_file: missing.rou.xml\n")
        try:
            load_scenario(bad)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("expected FileNotFoundError")
        open(bad, "w").write("name: x\n")
        try:
            load_scenario(bad)
        except ValueError:
            return
    raise AssertionError("expected ValueError")


def test_metrics_are_counted_per_simulated_second_including_yellow():
    fake = FakeTraci()
    env = _env("intersection.yaml", fake)
    env.reset()
    env.step(0)            # 1 simulated second, no switch
    m = env.metrics()
    assert m["mean_queue"] == 16.0 and m["arrived"] == 1
    assert np.isclose(m["avg_wait_per_vehicle"], 16.0 / 2)   # 16 vehicle-seconds / 2 departed
    env.step(1)            # switch: 3 s yellow + 1 s green = 4 more simulated seconds
    m = env.metrics()
    assert fake.t == 5 and m["arrived"] == 5
    assert np.isclose(m["throughput_per_hour"], 5 * 3600 / 5)
    assert np.isclose(m["mean_queue"], 16.0)       # still averaged over all 5 seconds
    assert np.isclose(m["mean_backlog"], 3.0)      # 3 vehicles waiting to be inserted, every second
    assert np.isclose(m["mean_total_waiting"], 19.0)
    assert m["switches"] == 1 and np.isclose(m["ns_green_fraction"], 0.5)   # one NS step, one EW step


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
