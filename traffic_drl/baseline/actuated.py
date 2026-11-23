"""Density-responsive ("actuated") signal controller: a stronger baseline.

Nepal's first AI-enabled signals (Lalitpur, Kupondole to Jawalakhel, 2024) count
vehicles with detectors and give the green to the heavier approach. This controller
does the same in the simulator:

  * keep the current green for at least `min_green` seconds;
  * after that, if nobody is on the other axis's approaches, keep the green;
  * switch when the current axis has no vehicles left (count <= `gap_queue`), when the
    other axis holds more than `ratio` times the current axis's vehicles, or when
    `max_green` is reached and the other axis has vehicles waiting.

DEMAND IS COUNTED WITH ALL VEHICLES ON THE APPROACH (moving ones included), like a
detector would, through `env.approach_vehicle_counts()` once the agent is attached to
an environment. Counting only *halted* vehicles (the learning agents' queue feature)
is wrong for this rule: while a lane has green its vehicles are moving, so its halted
count is about zero and the controller gaps out almost immediately. The first version
of this controller did exactly that and lost badly to the fixed timer (see
results/tuning/actuated); without an attached environment it still falls back to the
halted-queue state so it can be unit tested.

It has the same act() interface as the learning agents, so the same evaluate() loop
and metrics apply. Its few parameters should be tuned on selection seeds (not on the
test seeds), exactly as the DQN's settings are.
"""

import numpy as np

from traffic_drl.env import features

_NS_NAMES = ("north", "south")


class DensityActuatedAgent:
    def __init__(self, queue_idx, phase_idx, elapsed_idx, ns_cols, ew_cols, queue_scale: float,
                 elapsed_scale: float, min_green: float = 10.0, max_green: float = 60.0,
                 gap_queue: float = 0.0, ratio: float = 1.5, vehicles_idx=None, vehicle_scale: float = 1.0):
        self.queue_idx, self.phase_idx, self.elapsed_idx = queue_idx, phase_idx, elapsed_idx
        self.ns_cols, self.ew_cols = list(ns_cols), list(ew_cols)
        self.queue_scale, self.elapsed_scale = queue_scale, elapsed_scale
        self.min_green, self.max_green = float(min_green), float(max_green)
        self.gap_queue, self.ratio = float(gap_queue), float(ratio)
        self.vehicles_idx, self.vehicle_scale = vehicles_idx, vehicle_scale
        self.env = None

    @classmethod
    def from_config(cls, config: dict, **params) -> "DensityActuatedAgent":
        cfg = features.state_config(config)
        feats = cfg["features"]
        for needed in ("queue", "phase", "phase_elapsed"):
            if needed not in feats:
                raise ValueError(f"the actuated controller needs the '{needed}' state feature")
        n_app, n_act = len(config["approaches"]), 2
        sizes = {"queue": n_app, "waiting_time": n_app, "phase": n_act, "phase_elapsed": 1, "backlog": 1,
                 "vehicles": n_app}
        offsets, pos = {}, 0
        for f in feats:
            offsets[f] = pos
            pos += sizes[f]
        names = [a["name"] for a in config["approaches"]]
        ns = [i for i, n in enumerate(names) if n in _NS_NAMES]
        ew = [i for i, n in enumerate(names) if n not in _NS_NAMES]
        return cls(queue_idx=offsets["queue"], phase_idx=offsets["phase"], elapsed_idx=offsets["phase_elapsed"],
                   ns_cols=ns, ew_cols=ew, queue_scale=cfg["queue_scale"],
                   elapsed_scale=cfg["phase_elapsed_scale"], vehicles_idx=offsets.get("vehicles"),
                   vehicle_scale=cfg["vehicle_scale"], **params)

    def attach(self, env) -> "DensityActuatedAgent":
        """Give the controller detector-style counts from the environment (all vehicles on each approach)."""
        self.env = env
        return self

    def _demand(self, s) -> np.ndarray:
        if self.env is not None and hasattr(self.env, "approach_vehicle_counts"):
            return np.asarray(self.env.approach_vehicle_counts(), dtype=np.float64)
        if self.vehicles_idx is not None:          # the state already carries detector-style counts
            return s[self.vehicles_idx:self.vehicles_idx + len(self.ns_cols) + len(self.ew_cols)] * self.vehicle_scale
        return s[self.queue_idx:self.queue_idx + len(self.ns_cols) + len(self.ew_cols)] * self.queue_scale

    def act(self, state, greedy: bool = True) -> int:
        s = np.asarray(state, dtype=np.float64)
        demand = self._demand(s)
        current = int(np.argmax(s[self.phase_idx:self.phase_idx + 2]))     # 0 = north-south green, 1 = east-west
        elapsed = s[self.elapsed_idx] * self.elapsed_scale
        ns_q, ew_q = float(demand[self.ns_cols].sum()), float(demand[self.ew_cols].sum())
        cur_q, other_q = (ns_q, ew_q) if current == 0 else (ew_q, ns_q)
        other = 1 - current

        if elapsed < self.min_green or other_q <= 0:
            return current
        if elapsed >= self.max_green or cur_q <= self.gap_queue or other_q > self.ratio * cur_q:
            return other
        return current

    def reset(self) -> None:
        pass
