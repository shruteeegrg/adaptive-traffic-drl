"""Fixed-size experience replay buffer (ring buffer over numpy arrays).

Sampling past transitions uniformly at random breaks the correlation
between consecutive simulation steps, which is what makes DQN training
stable.
"""

import numpy as np


class ReplayBuffer:
    def __init__(self, capacity: int, state_dim: int, seed: int = 0):
        self.capacity = capacity
        self.states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.float32)
        self.rng = np.random.default_rng(seed)
        self._next = 0
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def add(self, state, action, reward, next_state, done) -> None:
        i = self._next
        self.states[i], self.actions[i], self.rewards[i] = state, action, reward
        self.next_states[i], self.dones[i] = next_state, float(done)
        self._next = (i + 1) % self.capacity  # overwrite the oldest when full
        self._size = min(self._size + 1, self.capacity)

    def sample(self, batch_size: int):
        if batch_size > self._size:
            raise ValueError(f"cannot sample {batch_size} from a buffer holding {self._size}")
        idx = self.rng.choice(self._size, size=batch_size, replace=False)
        return (self.states[idx], self.actions[idx], self.rewards[idx],
                self.next_states[idx], self.dones[idx])
