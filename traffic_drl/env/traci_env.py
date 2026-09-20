"""Config-driven SUMO/TraCI environment wrapper.

TraciEnv exposes the standard RL reset()/step(action) interface, but every
intersection-specific detail (which files, which junction, which lanes,
how many phases) comes from a YAML config (see configs/intersection.yaml)
rather than being hardcoded here -- pointing this at a different
intersection means writing a new config, not editing this file.

Action space: 0 = request "north_south_green", 1 = request "east_west_green".
If the requested green differs from the currently active one, the
environment inserts the yellow clearance phase automatically for
`yellow_duration` seconds before switching -- an agent never selects
yellow directly, and can never cause an unsafe green-to-green jump.

State: for each configured approach, the halting (queued) vehicle count
on its incoming edge -- i.e. a small numerical vector, not pixels, per the
proposal's own risk mitigation (keeps training CPU-only and fast).

Reward: negative sum of queue lengths across all approaches (minimizing
this is equivalent to minimizing total intersection delay).
"""

import os
import sys

import numpy as np

from traffic_drl.config import load_config

# SUMO ships its Python helper modules (traci, sumolib) under
# $SUMO_HOME/tools rather than on a normal pip-installed path -- this is
# the standard way SUMO/TraCI projects pick them up.
if "SUMO_HOME" in os.environ:
    tools_path = os.path.join(os.environ["SUMO_HOME"], "tools")
    if tools_path not in sys.path:
        sys.path.append(tools_path)

import traci  # noqa: E402  (import after sys.path setup, see above)

GREEN_PHASES = {0: 0, 1: 2}  # action -> tlLogic phase index (see intersection.yaml)
YELLOW_FOR = {0: 3, 2: 1}    # green phase index -> the yellow phase that clears it


class TraciEnv:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.tls_id = self.config["traffic_light_id"]
        self.step_length = float(self.config.get("step_length", 1.0))
        self.episode_length = float(self.config.get("episode_length", 3600))
        self.yellow_duration = float(self.config.get("yellow_duration", 3))
        self.gui = bool(self.config.get("gui", False))
        self.approaches = self.config["approaches"]

        self._connected = False
        self._current_green_phase = None  # tlLogic phase index currently active
        self._elapsed = 0.0

    def _sumo_binary(self) -> str:
        return "sumo-gui" if self.gui else "sumo"

    def reset(self):
        if self._connected:
            self.close()

        cmd = [
            self._sumo_binary(),
            "-c", self.config["sumocfg_file"],
            "--step-length", str(self.step_length),
            "--no-warnings", "true",
            "--no-step-log", "true",
        ]
        traci.start(cmd)
        self._connected = True
        self._elapsed = 0.0

        # Start on the north-south green phase (action 0) by convention.
        traci.trafficlight.setPhase(self.tls_id, GREEN_PHASES[0])
        self._current_green_phase = GREEN_PHASES[0]

        return self._get_state()

    def step(self, action: int):
        if action not in GREEN_PHASES:
            raise ValueError(f"action must be one of {list(GREEN_PHASES)}, got {action}")

        requested_phase = GREEN_PHASES[action]

        if self._current_green_phase is not None and requested_phase != self._current_green_phase:
            # Switching green -- clear the intersection with a yellow phase
            # first rather than jumping straight to a conflicting green.
            traci.trafficlight.setPhase(self.tls_id, YELLOW_FOR[self._current_green_phase])
            self._advance(self.yellow_duration)

        traci.trafficlight.setPhase(self.tls_id, requested_phase)
        self._current_green_phase = requested_phase
        self._advance(self.step_length)

        state = self._get_state()
        reward = self._get_reward(state)
        done = (
            self._elapsed >= self.episode_length
            or traci.simulation.getMinExpectedNumber() == 0
        )
        info = {"elapsed": self._elapsed}
        return state, reward, done, info

    def _advance(self, seconds: float):
        n_steps = max(1, round(seconds / self.step_length))
        for _ in range(n_steps):
            traci.simulationStep()
            self._elapsed += self.step_length

    def _get_state(self) -> np.ndarray:
        return np.array(
            [traci.edge.getLastStepHaltingNumber(a["incoming_edge"]) for a in self.approaches],
            dtype=np.float32,
        )

    def _get_reward(self, state: np.ndarray) -> float:
        return -float(state.sum())

    def close(self):
        if self._connected:
            traci.close()
            self._connected = False
