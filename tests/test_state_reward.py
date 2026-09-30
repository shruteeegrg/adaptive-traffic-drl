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
    assert features.compute_reward(rcfg, [3, 1, 0, 2], [9, 9, 9, 9], True) == -6.0


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
    r = features.reward_config({"reward": {"queue_weight": 1, "wait_weight": 0.5,
                                           "switch_penalty": 4, "reward_scale": 2}})
    assert features.compute_reward(r, [2, 2], [10, 0], False) == -(4 + 5) / 2
    assert features.compute_reward(r, [2, 2], [10, 0], True) == -(4 + 5 + 4) / 2


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
        self.trafficlight = self
        self.edge = self
        self.simulation = self

    def start(self, cmd): pass
    def close(self): pass
    def simulationStep(self): self.t += 1
    def setPhase(self, tls, phase): self.phases.append(phase)
    def getLastStepHaltingNumber(self, e): return 4
    def getWaitingTime(self, e): return 20.0
    def getMinExpectedNumber(self): return 1


def _env(config_name, monkeypatch_fake):
    traci_env.traci = monkeypatch_fake
    return traci_env.TraciEnv(os.path.join(ROOT, "configs", config_name))


def test_traci_env_default_config_is_unchanged():
    fake = FakeTraci()
    env = _env("intersection.yaml", fake)
    s = env.reset()
    assert s.tolist() == [4, 4, 4, 4]
    s, r, done, _ = env.step(0)
    assert r == -16.0 and not done


def test_traci_env_full_state_tracks_phase_and_switch_penalty():
    fake = FakeTraci()
    env = _env("dqn.yaml", fake)
    s = env.reset()
    assert s.shape == (11,) == (env.state_size,)
    s, r, _, _ = env.step(0)                       # stay on NS: no switch
    assert s[8:10].tolist() == [1, 0] and np.isclose(s[10], 1 / 60)
    assert np.isclose(r, -(16 + 0.05 * 80) / 10)
    s, _, _, _ = env.step(0)
    assert np.isclose(s[10], 2 / 60)               # time-in-phase accumulates
    s, r, _, _ = env.step(1)                       # switch to EW: penalty + yellow clearance
    assert s[8:10].tolist() == [0, 1] and np.isclose(s[10], 1 / 60)
    assert np.isclose(r, -(16 + 4 + 2) / 10)
    assert 3 in fake.phases                        # yellow inserted before the new green


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
