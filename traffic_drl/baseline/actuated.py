"""Density-responsive ("actuated") signal controller: a stronger baseline.

Nepal's first AI-enabled signals (Lalitpur, Kupondole to Jawalakhel, 2024)
count vehicles with detectors and give the green to the heavier approach.
This controller does the same thing in the simulator, from the same queue
counts the DQN sees:

  * keep the current green for at least `min_green` seconds;
  * after that, if nobody is waiting on the other axis, keep the green;
  * switch when the current axis has emptied (queue <= `gap_queue`), when the
    other axis holds more than `ratio` times the current axis's queue, or when
    `max_green` is reached and the other axis has waiting vehicles.

It has the same act() interface as the learning agents, so the same evaluate()
loop and metrics apply. Its few parameters should be tuned on selection seeds
(not on the test seeds), exactly as the DQN's settings are.
"""

import numpy as np

from traffic_drl.env import features

_NS_NAMES = ("north", "south")


class DensityActuatedAgent:
    def __init__(self, queue_idx, phase_idx, elapsed_idx, ns_cols, ew_cols, queue_scale: float,
                 elapsed_scale: float, min_green: float = 10.0, max_green: float = 60.0,
                 gap_queue: float = 1.0, ratio: float = 1.5):
        self.queue_idx, self.phase_idx, self.elapsed_idx = queue_idx, phase_idx, elapsed_idx
        self.ns_cols, self.ew_cols = list(ns_cols), list(ew_cols)
        self.queue_scale, self.elapsed_scale = queue_scale, elapsed_scale
        self.min_green, self.max_green = float(min_green), float(max_green)
        self.gap_queue, self.ratio = float(gap_queue), float(ratio)

    @classmethod
    def from_config(cls, config: dict, **params) -> "DensityActuatedAgent":
        cfg = features.state_config(config)
        feats = cfg["features"]
        for needed in ("queue", "phase", "phase_elapsed"):
            if needed not in feats:
                raise ValueError(f"the actuated controller needs the '{needed}' state feature")
        n_app, n_act = len(config["approaches"]), 2
        sizes = {"queue": n_app, "waiting_time": n_app, "phase": n_act, "phase_elapsed": 1, "backlog": 1}
        offsets, pos = {}, 0
        for f in feats:
            offsets[f] = pos
            pos += sizes[f]
        names = [a["name"] for a in config["approaches"]]
        ns = [i for i, n in enumerate(names) if n in _NS_NAMES]
        ew = [i for i, n in enumerate(names) if n not in _NS_NAMES]
        return cls(queue_idx=offsets["queue"], phase_idx=offsets["phase"], elapsed_idx=offsets["phase_elapsed"],
                   ns_cols=ns, ew_cols=ew, queue_scale=cfg["queue_scale"],
                   elapsed_scale=cfg["phase_elapsed_scale"], **params)

    def act(self, state, greedy: bool = True) -> int:
        s = np.asarray(state, dtype=np.float64)
        queues = s[self.queue_idx:self.queue_idx + len(self.ns_cols) + len(self.ew_cols)] * self.queue_scale
        current = int(np.argmax(s[self.phase_idx:self.phase_idx + 2]))     # 0 = north-south green, 1 = east-west
        elapsed = s[self.elapsed_idx] * self.elapsed_scale
        ns_q, ew_q = float(queues[self.ns_cols].sum()), float(queues[self.ew_cols].sum())
        cur_q, other_q = (ns_q, ew_q) if current == 0 else (ew_q, ns_q)
        other = 1 - current

        if elapsed < self.min_green or other_q <= 0:
            return current
        if elapsed >= self.max_green or cur_q <= self.gap_queue or other_q > self.ratio * cur_q:
            return other
        return current

    def reset(self) -> None:
        pass
