"""Fixed-size experience replay buffer (ring buffer over numpy arrays).

Sampling past transitions uniformly at random breaks the correlation
between consecutive simulation steps, which is what makes DQN training
stable.
"""

import numpy as np


class ReplayBuffer:
    def __init__(self, capacity: int, state_dim: int, seed: int = 0, frozen: bool = False):
        self.capacity = capacity
        self.frozen = frozen           # frozen: once full, new transitions are dropped (nothing is overwritten)
        self.experts = np.zeros(capacity, dtype=np.float32)   # 1 = the action was a teacher's choice
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

    def add(self, state, action, reward, next_state, done, expert: float = 0.0) -> None:
        if self.frozen and self._size >= self.capacity:
            return
        i = self._next
        self.states[i], self.actions[i], self.rewards[i] = state, action, reward
        self.next_states[i], self.dones[i], self.experts[i] = next_state, float(done), float(expert)
        self._next = (i + 1) % self.capacity  # overwrite the oldest when full
        self._size = min(self._size + 1, self.capacity)

    def sample(self, batch_size: int):
        if batch_size > self._size:
            raise ValueError(f"cannot sample {batch_size} from a buffer holding {self._size}")
        idx = self.rng.choice(self._size, size=batch_size, replace=False)
        return (self.states[idx], self.actions[idx], self.rewards[idx],
                self.next_states[idx], self.dones[idx])

    def sample_flags(self, batch_size: int, replace: bool = False):
        """Like sample(), plus the expert flags; `replace` lets a small buffer fill a larger batch."""
        if self._size == 0 or (not replace and batch_size > self._size):
            raise ValueError(f"cannot sample {batch_size} from a buffer holding {self._size}")
        idx = self.rng.choice(self._size, size=batch_size, replace=replace)
        return (self.states[idx], self.actions[idx], self.rewards[idx],
                self.next_states[idx], self.dones[idx], self.experts[idx])
