"""Fixed-time baseline tests (no SUMO needed)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl.agent import evaluate  # noqa: E402
from traffic_drl.baseline import FixedTimeAgent  # noqa: E402
from traffic_drl.env import SimpleQueueEnv  # noqa: E402


def test_cycles_with_constant_green_duration():
    agent = FixedTimeAgent(green_steps=3)
    assert [agent.act() for _ in range(9)] == [0, 0, 0, 1, 1, 1, 0, 0, 0]


def test_reset_restarts_cycle():
    agent = FixedTimeAgent(green_steps=2)
    agent.act(); agent.act(); agent.act()
    agent.reset()
    assert agent.act() == 0


def test_runs_through_the_same_evaluate_loop_as_learners():
    result = evaluate(SimpleQueueEnv(seed=0), FixedTimeAgent(green_steps=10), episodes=2)
    assert result["reward"] < 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
