"""Simplified two-direction queue model (Week 3 convergence testbed).

A pure-Python stand-in for the SUMO intersection, exposing the same
reset()/step(action) contract as `TraciEnv`: action 0 serves the
north-south queue, action 1 serves the east-west queue, switching costs
`yellow_duration` seconds of lost service, and reward is the negative
total queue length. It exists so the Q-table agent's convergence can be
checked in seconds and deterministically (seeded), with no SUMO process.
It is a sanity check for the learning code, not a model of real traffic.
"""

import numpy as np


class SimpleQueueEnv:
    def __init__(
        self,
        arrival_probs=(0.35, 0.15),
        service_prob: float = 0.8,
        yellow_duration: int = 3,
        episode_length: int = 300,
        max_queue: int = 30,
        seed: int = 0,
    ):
        self.arrival_probs = np.asarray(arrival_probs, dtype=np.float64)
        self.service_prob = service_prob
        self.yellow_duration = yellow_duration
        self.episode_length = episode_length
        self.max_queue = max_queue
        self.seed = seed
        self._episode = 0

    def reset(self):
        # A fresh but reproducible stream per episode.
        self.rng = np.random.default_rng(self.seed + self._episode)
        self._episode += 1
        self.queues = np.zeros(2, dtype=np.int64)
        self.green = 0
        self._elapsed = 0
        return self._state()

    def _tick(self, serving):
        arrivals = self.rng.random(2) < self.arrival_probs
        self.queues = np.minimum(self.queues + arrivals, self.max_queue)
        if serving and self.queues[self.green] > 0 and self.rng.random() < self.service_prob:
            self.queues[self.green] -= 1
        self._elapsed += 1

    def step(self, action: int):
        if action not in (0, 1):
            raise ValueError(f"action must be 0 or 1, got {action}")
        if action != self.green:
            for _ in range(self.yellow_duration):
                self._tick(serving=False)
            self.green = action
        self._tick(serving=True)
        state = self._state()
        reward = -float(state.sum())
        done = self._elapsed >= self.episode_length
        return state, reward, done, {"elapsed": self._elapsed}

    def _state(self) -> np.ndarray:
        return self.queues.astype(np.float32)

    def close(self):
        pass
