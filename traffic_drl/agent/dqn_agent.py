"""Deep Q-Network agent (Week 5), from scratch on the hand-written MLP.

Standard DQN (Mnih et al. 2015): an online network picks actions and is
trained by gradient descent on the TD error; a periodically-synced target
network supplies the bootstrap value so the regression target doesn't
chase itself; transitions come from a replay buffer.

It exposes the same interface as QTableAgent -- act(state, greedy),
update(s, a, r, s2, done), decay_epsilon() -- so one training loop
(traffic_drl.agent.training) drives both. Here `update` stores the
transition and runs a gradient step every `train_every` env steps once
`learn_start` transitions are buffered. Hyperparameters come from the
`dqn:` config section.
"""

import numpy as np

from traffic_drl.agent.nn import MLP, Adam, huber_loss, mse_loss
from traffic_drl.agent.replay_buffer import ReplayBuffer

# Keys in the `dqn:` config section that belong to the training loop or
# to other consumers, not to the agent constructor.
_LOOP_KEYS = ("episodes", "max_steps", "eval_every")


class DQNAgent:
    def __init__(
        self,
        state_dim: int,
        n_actions: int = 2,
        hidden_sizes=(64, 64),
        learning_rate: float = 1e-3,
        gamma: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.9,
        batch_size: int = 64,
        buffer_size: int = 20000,
        learn_start: int = 500,
        train_every: int = 1,
        target_sync_steps: int = 200,
        loss: str = "huber",
        seed: int = 0,
        double_dqn: bool = False,
    ):
        if loss not in ("huber", "mse"):
            raise ValueError("loss must be 'huber' or 'mse'")
        self.state_dim, self.n_actions = state_dim, n_actions
        self.gamma = gamma
        self.epsilon, self.epsilon_end, self.epsilon_decay = epsilon_start, epsilon_end, epsilon_decay
        self.batch_size, self.learn_start = batch_size, learn_start
        self.train_every, self.target_sync_steps = train_every, target_sync_steps
        self.double_dqn = bool(double_dqn)   # choose the next action with the online net, score it with the target net
        self.loss_fn = huber_loss if loss == "huber" else mse_loss

        sizes = [state_dim, *hidden_sizes, n_actions]
        self.online = MLP(sizes, seed=seed)
        self.target = MLP(sizes, seed=seed)
        self.target.copy_from(self.online)
        self.optimizer = Adam(self.online, lr=learning_rate)
        self.buffer = ReplayBuffer(buffer_size, state_dim, seed=seed)
        self.rng = np.random.default_rng(seed)

        self.steps = 0          # env transitions seen
        self.learn_steps = 0    # gradient updates taken
        self.last_loss = None
        self._losses = []

    @classmethod
    def from_config(cls, config: dict, state_dim: int, n_actions: int = 2) -> "DQNAgent":
        params = dict(config.get("dqn", {}))
        for k in _LOOP_KEYS:
            params.pop(k, None)
        if "learning_rate" in params:
            params["learning_rate"] = float(params["learning_rate"])
        return cls(state_dim=state_dim, n_actions=n_actions, **params)

    def q_values(self, state) -> np.ndarray:
        return self.online.forward(state, cache=False)[0]

    def act(self, state, greedy: bool = False) -> int:
        if not greedy and self.rng.random() < self.epsilon:
            return int(self.rng.integers(self.n_actions))
        q = self.q_values(state)
        return int(self.rng.choice(np.flatnonzero(q == q.max())))

    def update(self, state, action, reward, next_state, done) -> None:
        self.buffer.add(state, action, reward, next_state, done)
        self.steps += 1
        if len(self.buffer) >= max(self.learn_start, self.batch_size) and self.steps % self.train_every == 0:
            self.learn()
        if self.steps % self.target_sync_steps == 0:
            self.target.copy_from(self.online)

    def learn(self) -> float:
        s, a, r, s2, d = self.buffer.sample(self.batch_size)
        # Bellman target from the *target* network; terminal states don't bootstrap.
        next_q = self.target.forward(s2, cache=False)
        if self.double_dqn:
            # Double DQN: the online network picks the action, the target network values it,
            # which curbs the over-estimation of plain max-over-target (van Hasselt et al., 2016).
            best = self.online.forward(s2, cache=False).argmax(axis=1)
            bootstrap = next_q[np.arange(self.batch_size), best]
        else:
            bootstrap = next_q.max(axis=1)
        y = r + self.gamma * (1.0 - d) * bootstrap

        pred = self.online.forward(s)
        rows = np.arange(self.batch_size)
        target = pred.copy()
        target[rows, a] = y
        mask = np.zeros_like(pred)
        mask[rows, a] = 1.0  # loss only on the action actually taken
        loss, grad = self.loss_fn(pred, target, mask)
        self.optimizer.step(*self.online.backward(grad))

        self.learn_steps += 1
        self.last_loss = loss
        self._losses.append(loss)
        return loss

    def pop_mean_loss(self):
        """Mean loss since the last call (None if no gradient step ran);
        the training loop logs one value per episode."""
        mean = float(np.mean(self._losses)) if self._losses else None
        self._losses = []
        return mean

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def save(self, path: str) -> None:
        self.online.save(path)

    def load(self, path: str) -> None:
        self.online.load(path)
        self.target.copy_from(self.online)
