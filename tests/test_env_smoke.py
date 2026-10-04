"""Week 2 smoke test: proves the config-driven SUMO/TraCI environment runs
headlessly and repeatably -- the "done when" criterion in DELIVERABLES.md
for the Simulation Environment deliverable.

This is intentionally not a unit test of agent logic (there's no agent
yet) -- it drives the environment with a fixed alternating policy purely
to confirm reset()/step() work end to end against a real SUMO process.

Run with SUMO installed and SUMO_HOME set:
    python -m pytest tests/test_env_smoke.py -v
or directly:
    python tests/test_env_smoke.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traffic_drl.env import TraciEnv  # noqa: E402


def run_smoke_test(config_path="configs/intersection.yaml", n_steps=200):
    env = TraciEnv(config_path)
    state = env.reset()
    assert state.shape == (env.state_size,), f"expected {env.state_size} state elements, got {state.shape}"

    total_reward = 0.0
    action = 0
    for i in range(n_steps):
        # Alternate the requested phase every 30 steps, purely to exercise
        # the yellow-clearance transition logic in TraciEnv.step().
        if i % 30 == 0:
            action = 1 - action
        state, reward, done, info = env.step(action)
        total_reward += reward
        if done:
            break

    env.close()
    print(f"Smoke test OK: ran {i + 1} steps, total_reward={total_reward:.1f}, final_state={state}")
    return True


if __name__ == "__main__":
    run_smoke_test()
