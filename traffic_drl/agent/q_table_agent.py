"""Tabular Q-learning agent (Week 3 baseline).

Implemented from scratch with numpy -- no RL library. The raw state is a
vector of per-approach queue lengths; it is discretized into a few
buckets per approach so the Q-table stays small enough to converge.
This is the proposal's own risk mitigation: de-risk learning on a coarse
state space before scaling to a DQN over the full state.

The agent only assumes the env contract (state vector in, integer action
out), so the same class drives the SUMO `TraciEnv` and the toy queue
model used for fast convergence checks. Hyperparameters come from the
`qtable:` section of the config, not from constants here.
"""

import json

import numpy as np


class QTableAgent:
    def __init__(
        self,
        n_actions: int = 2,
        queue_bins=(1, 4, 8),
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.95,
        seed: int = 0,
    ):
        self.n_actions = n_actions
        self.queue_bins = np.asarray(queue_bins, dtype=np.float32)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.rng = np.random.default_rng(seed)
        # Sparse table: only states actually visited get a row.
        self.q = {}

    @classmethod
    def from_config(cls, config: dict, n_actions: int = 2) -> "QTableAgent":
        params = dict(config.get("qtable", {}))
        # Keys that belong to the training loop, not the agent.
        params.pop("episodes", None)
        params.pop("max_steps", None)
        return cls(n_actions=n_actions, **params)

    def discretize(self, state) -> tuple:
        """Map a raw queue-length vector to a tuple of bucket indices."""
        return tuple(int(i) for i in np.digitize(np.asarray(state, dtype=np.float32), self.queue_bins))

    def _row(self, key: tuple) -> np.ndarray:
        if key not in self.q:
            self.q[key] = np.zeros(self.n_actions, dtype=np.float64)
        return self.q[key]

    def act(self, state, greedy: bool = False) -> int:
        row = self._row(self.discretize(state))
        if not greedy and self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.n_actions))
        # Break ties randomly so an untrained row isn't biased to action 0.
        best = np.flatnonzero(row == row.max())
        return int(self.rng.choice(best))

    def update(self, state, action: int, reward: float, next_state, done: bool) -> None:
        row = self._row(self.discretize(state))
        next_value = 0.0 if done else float(self._row(self.discretize(next_state)).max())
        target = reward + self.gamma * next_value
        row[action] += self.alpha * (target - row[action])

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def save(self, path: str) -> None:
        payload = {
            "n_actions": self.n_actions,
            "queue_bins": self.queue_bins.tolist(),
            "q": {",".join(map(str, k)): v.tolist() for k, v in self.q.items()},
        }
        with open(path, "w") as f:
            json.dump(payload, f)

    def load(self, path: str) -> None:
        with open(path) as f:
            payload = json.load(f)
        self.n_actions = payload["n_actions"]
        self.queue_bins = np.asarray(payload["queue_bins"], dtype=np.float32)
        self.q = {
            tuple(int(i) for i in k.split(",")): np.asarray(v, dtype=np.float64)
            for k, v in payload["q"].items()
        }
