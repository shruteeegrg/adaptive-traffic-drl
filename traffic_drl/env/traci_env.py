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

Week 4: the state vector and reward are now built by traffic_drl.env.features
from the optional `state:` / `reward:` config sections (queue, waiting
time, current phase, time in phase; queue/wait/switch-penalty weights).
With those sections absent the behaviour above is unchanged.
"""

import os
import sys

import numpy as np

from traffic_drl.config import load_config, load_scenario
from traffic_drl.env import features

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
    def __init__(self, config_path: str, scenario=None, seed: int = 0):
        """`scenario` is an optional path to a scenario YAML (e.g.
        configs/scenarios/rush_hour.yaml), a comma-separated string of paths,
        or a list of them; its route file replaces the intersection's default
        demand. With several, training episodes cycle through them in order
        (mixed-scenario training); with none given the config's own
        `scenarios:` list is used, if it has one."""
        self.config = load_config(config_path)
        if isinstance(scenario, str):
            scenario = [p.strip() for p in scenario.split(",") if p.strip()]
        paths = list(scenario) if scenario else list(self.config.get("scenarios") or [])
        self.scenarios = [load_scenario(p) for p in paths]
        self.scenario_names = [sc.get("name", os.path.basename(sc["route_file"])) for sc in self.scenarios]
        self.force_scenario = None   # evaluate() pins one scenario here; None = cycle
        self._train_episodes = 0     # training resets so far (drives the cycle)
        self.current_scenario = None
        # Each reset() launches SUMO with seed = seed_base + (number of resets
        # so far), so episodes see different driver behaviour instead of
        # replaying one identical run. evaluate() moves seed_base far away
        # from the training seeds so evaluation uses unseen realizations.
        self.seed_base = seed
        self._n_resets = 0
        self.tls_id = self.config["traffic_light_id"]
        self.step_length = float(self.config.get("step_length", 1.0))
        self.episode_length = float(self.config.get("episode_length", 3600))
        self.yellow_duration = float(self.config.get("yellow_duration", 3))
        # Seconds the chosen green is held per decision (SUMO still steps at
        # step_length). >1 acts as a minimum green and shortens episodes.
        self.decision_interval = float(self.config.get("decision_interval", self.step_length))
        self.gui = bool(self.config.get("gui", False))
        self.approaches = self.config["approaches"]
        self.state_cfg = features.state_config(self.config)
        self.reward_cfg = features.reward_config(self.config)
        self.n_actions = len(GREEN_PHASES)
        self.state_size = features.state_size(self.state_cfg, len(self.approaches), self.n_actions)
        self._action = 0
        self._phase_elapsed = 0.0

        self._connected = False
        self._current_green_phase = None  # tlLogic phase index currently active
        self._elapsed = 0.0
        self._reset_metrics()

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
            "--seed", str(self.seed_base + self._n_resets),
        ]
        self._n_resets += 1
        if self.scenarios:
            if self.force_scenario is not None:
                idx = self.force_scenario
            else:
                idx = self._train_episodes % len(self.scenarios)
                self._train_episodes += 1
            self.current_scenario = self.scenario_names[idx]
            cmd += ["--route-files", self.scenarios[idx]["route_file"]]  # overrides the sumocfg's demand
        traci.start(cmd)
        self._connected = True
        self._elapsed = 0.0
        self._action = 0
        self._phase_elapsed = 0.0
        self._reset_metrics()
        self._step_cost = 0.0

        # Start on the north-south green phase (action 0) by convention.
        traci.trafficlight.setPhase(self.tls_id, GREEN_PHASES[0])
        self._current_green_phase = GREEN_PHASES[0]

        return self._get_state()

    def step(self, action: int):
        if action not in GREEN_PHASES:
            raise ValueError(f"action must be one of {list(GREEN_PHASES)}, got {action}")

        requested_phase = GREEN_PHASES[action]
        switched = requested_phase != self._current_green_phase
        self._step_cost = 0.0  # cost accrued per simulated second over this decision

        if self._current_green_phase is not None and requested_phase != self._current_green_phase:
            # Switching green -- clear the intersection with a yellow phase
            # first rather than jumping straight to a conflicting green.
            traci.trafficlight.setPhase(self.tls_id, YELLOW_FOR[self._current_green_phase])
            self._advance(self.yellow_duration)

        traci.trafficlight.setPhase(self.tls_id, requested_phase)
        self._current_green_phase = requested_phase
        self._advance(self.decision_interval)

        self._switches += int(switched)
        self._green_seconds[action] += self.decision_interval
        self._phase_elapsed = self.decision_interval if switched else self._phase_elapsed + self.decision_interval
        self._action = action
        state = self._get_state()
        reward = features.compute_reward(self.reward_cfg, self._step_cost, switched)
        done = (
            self._elapsed >= self.episode_length
            or traci.simulation.getMinExpectedNumber() == 0
        )
        info = {"elapsed": self._elapsed, **self.metrics()}
        return state, reward, done, info

    def _reset_metrics(self):
        self._queue_seconds = 0.0   # sum over simulated seconds of vehicles halted at the junction
        self._backlog_seconds = 0.0  # same, for vehicles waiting outside the network to be inserted
        self._arrived = 0           # vehicles that completed their trip
        self._departed = 0          # vehicles that entered the network
        self._switches = 0          # phase changes the agent caused
        self._green_seconds = [0.0, 0.0]  # green time given to each action's phase

    def _advance(self, seconds: float):
        n_steps = max(1, round(seconds / self.step_length))
        for _ in range(n_steps):
            traci.simulationStep()
            self._elapsed += self.step_length
            # Measured every simulated second -- including yellow time -- so
            # the metrics don't depend on how often the agent switches.
            queue_now = sum(
                traci.edge.getLastStepHaltingNumber(a["incoming_edge"]) for a in self.approaches
            )
            self._queue_seconds += self.step_length * queue_now
            # Approach edges are short (~12 vehicles), so under heavy demand SUMO
            # holds the overflow in an insertion backlog that the halting
            # count above cannot see; count it too.
            backlog_now = len(traci.simulation.getPendingVehicles())
            self._backlog_seconds += self.step_length * backlog_now
            wait_now = (
                sum(traci.edge.getWaitingTime(a["incoming_edge"]) for a in self.approaches)
                if self.reward_cfg["wait_weight"] else 0.0
            )
            self._step_cost += self.step_length * features.accrue_cost(
                self.reward_cfg, queue_now, wait_now, backlog_now)
            self._arrived += traci.simulation.getArrivedNumber()
            self._departed += traci.simulation.getDepartedNumber()

    def metrics(self) -> dict:
        """Per-second evaluation metrics for the episode so far. These, not
        the training reward, are what the fixed-time comparison uses:
          mean_queue            average halted vehicles on the approach edges
          mean_backlog          average vehicles waiting outside to enter the network
          mean_total_waiting    mean_queue + mean_backlog -- the ranking metric
          avg_wait_per_vehicle  halted vehicle-seconds / vehicles entered (s)
          throughput_per_hour   completed trips, scaled to one hour
          switches              phase changes (flipping vs stuck policies)
          ns_green_fraction     share of green time given to north-south
        """
        elapsed = max(self._elapsed, 1e-9)
        mean_queue = self._queue_seconds / elapsed
        mean_backlog = self._backlog_seconds / elapsed
        return {
            "mean_queue": mean_queue,
            "mean_backlog": mean_backlog,
            "mean_total_waiting": mean_queue + mean_backlog,
            "avg_wait_per_vehicle": self._queue_seconds / max(self._departed, 1),
            "throughput_per_hour": self._arrived * 3600.0 / elapsed,
            "arrived": self._arrived,
            "switches": self._switches,
            "ns_green_fraction": self._green_seconds[0] / max(sum(self._green_seconds), 1e-9),
        }

    def _read_edges(self):
        edges = [a["incoming_edge"] for a in self.approaches]
        queues = [traci.edge.getLastStepHaltingNumber(e) for e in edges]
        waits = (
            [traci.edge.getWaitingTime(e) for e in edges]
            if "waiting_time" in self.state_cfg["features"]
            else [0.0] * len(edges)
        )
        return queues, waits

    def _get_state(self) -> np.ndarray:
        queues, waits = self._read_edges()
        backlog = (
            len(traci.simulation.getPendingVehicles()) if "backlog" in self.state_cfg["features"] else 0.0
        )
        return features.build_state(
            self.state_cfg, queues, waits, self._action, self._phase_elapsed, self.n_actions, backlog
        )

    def close(self):
        if self._connected:
            traci.close()
            self._connected = False
