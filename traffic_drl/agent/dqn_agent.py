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
_LOOP_KEYS = ("episodes", "max_steps", "eval_every", "eval_episodes", "pretrain")


def clip_by_global_norm(dW, db, max_norm: float):
    """Scale the gradient so its global L2 norm is at most `max_norm` (guards against rare huge updates)."""
    total = float(np.sqrt(sum(float((g.astype(np.float64) ** 2).sum()) for g in (*dW, *db))))
    if total <= max_norm or total == 0.0:
        return dW, db
    scale = max_norm / total
    return [g * scale for g in dW], [g * scale for g in db]


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
        target_tau: float = 0.0,
        grad_clip: float = 0.0,
        lr_decay: float = 1.0,
        lr_min: float = 1e-5,
        demo_fraction: float = 0.0,
        demo_margin: float = 1.0,
        demo_margin_weight: float = 1.0,
        demo_capacity: int = 30000,
        bootstrap_on_timeout: bool = False,
    ):
        if loss not in ("huber", "mse"):
            raise ValueError("loss must be 'huber' or 'mse'")
        self.state_dim, self.n_actions = state_dim, n_actions
        self.gamma = gamma
        self.epsilon, self.epsilon_end, self.epsilon_decay = epsilon_start, epsilon_end, epsilon_decay
        self.batch_size, self.learn_start = batch_size, learn_start
        self.train_every, self.target_sync_steps = train_every, target_sync_steps
        self.target_tau = float(target_tau)    # > 0: soft target update every gradient step instead of a hard copy
        self.grad_clip = float(grad_clip)      # > 0: clip the gradient's global norm
        self.lr_decay, self.lr_min = float(lr_decay), float(lr_min)   # learning rate x lr_decay after every episode
        # Learning from demonstrations (DQfD-style): teacher transitions live in a frozen buffer that is never
        # overwritten, a fraction `demo_fraction` of every batch comes from it, and a large-margin loss keeps the
        # teacher's action ranked above the alternatives on those rows.
        self.demo_fraction, self.demo_margin = float(demo_fraction), float(demo_margin)
        self.demo_margin_weight, self.demo_capacity = float(demo_margin_weight), int(demo_capacity)
        self.demo_buffer = None
        # True: an episode cut off by the time limit is not stored as terminal, so its last transition still
        # bootstraps from the next state. False (default) keeps the original behaviour.
        self.bootstrap_on_timeout = bool(bootstrap_on_timeout)
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
        learned = False
        if len(self.buffer) >= max(self.learn_start, self.batch_size) and self.steps % self.train_every == 0:
            self.learn()
            learned = True
        self._sync_target(learned)

    def add_demo(self, state, action, reward, next_state, done, expert: bool = True) -> None:
        """Store a teacher-run transition in the frozen demonstration buffer. `expert` marks actions the
        teacher chose (as opposed to random exploration noise); only those get the margin loss."""
        if self.demo_buffer is None:
            self.demo_buffer = ReplayBuffer(self.demo_capacity, self.state_dim, seed=int(self.rng.integers(1 << 31)),
                                            frozen=True)
        self.demo_buffer.add(state, action, reward, next_state, done, expert=float(expert))

    def _sample_batch(self):
        """A training batch; mixes in demonstrations when a frozen demo buffer exists."""
        n_demo = 0
        if self.demo_buffer is not None and len(self.demo_buffer) and self.demo_fraction > 0:
            n_demo = min(int(round(self.batch_size * self.demo_fraction)), len(self.demo_buffer))
        n_main = self.batch_size - n_demo
        s, a, r, s2, d = self.buffer.sample(n_main) if n_main <= len(self.buffer) else self.buffer.sample(len(self.buffer))
        e = np.zeros(len(a), dtype=np.float32)
        if n_demo:
            ds, da, dr, ds2, dd, de = self.demo_buffer.sample_flags(n_demo)
            s, a, r = np.concatenate([s, ds]), np.concatenate([a, da]), np.concatenate([r, dr])
            s2, d, e = np.concatenate([s2, ds2]), np.concatenate([d, dd]), np.concatenate([e, de])
        return s, a, r, s2, d, e

    def _sync_target(self, learned: bool) -> None:
        if self.target_tau > 0:
            if learned:
                self.target.soft_update(self.online, self.target_tau)
        elif self.steps % self.target_sync_steps == 0:
            self.target.copy_from(self.online)

    def offline_learn(self, n_steps: int) -> None:
        """Extra gradient steps on what is already in the replay buffer (used after seeding it with a
        teacher's transitions)."""
        if len(self.buffer) < self.batch_size:
            return
        for _ in range(n_steps):
            self.learn()
            self.steps += 1
            self._sync_target(True)

    def learn(self) -> float:
        s, a, r, s2, d, expert = self._sample_batch()
        n = len(a)
        # Bellman target from the *target* network; terminal states don't bootstrap.
        next_q = self.target.forward(s2, cache=False)
        if self.double_dqn:
            # Double DQN: the online network picks the action, the target network values it,
            # which curbs the over-estimation of plain max-over-target (van Hasselt et al., 2016).
            best = self.online.forward(s2, cache=False).argmax(axis=1)
            bootstrap = next_q[np.arange(n), best]
        else:
            bootstrap = next_q.max(axis=1)
        y = r + self.gamma * (1.0 - d) * bootstrap

        pred = self.online.forward(s)
        rows = np.arange(n)
        target = pred.copy()
        target[rows, a] = y
        mask = np.zeros_like(pred)
        mask[rows, a] = 1.0  # loss only on the action actually taken
        loss, grad = self.loss_fn(pred, target, mask)
        if self.demo_margin_weight > 0 and expert.any():
            grad = grad + self.demo_margin_weight * self._margin_grad(pred, a, expert)
        dW, db = self.online.backward(grad)
        if self.grad_clip > 0:
            dW, db = clip_by_global_norm(dW, db, self.grad_clip)
        self.optimizer.step(dW, db)

        self.learn_steps += 1
        self.last_loss = loss
        self._losses.append(loss)
        return loss

    def _margin_grad(self, pred, actions, expert):
        """Gradient (wrt pred) of the large-margin loss  max_a [Q(s,a) + margin*(a != a_E)] - Q(s,a_E)  on the
        rows whose action was the teacher's: it pushes the teacher's action above every other by `margin`."""
        n = pred.shape[0]
        penalty = self.demo_margin * (1.0 - np.eye(self.n_actions)[actions])
        j = (pred + penalty).argmax(axis=1)
        grad = np.zeros_like(pred)
        rows = np.flatnonzero((expert > 0) & (j != actions))
        grad[rows, j[rows]] += 1.0
        grad[rows, actions[rows]] -= 1.0
        return grad / n

    def pop_mean_loss(self):
        """Mean loss since the last call (None if no gradient step ran);
        the training loop logs one value per episode."""
        mean = float(np.mean(self._losses)) if self._losses else None
        self._losses = []
        return mean

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        if self.lr_decay != 1.0:
            self.optimizer.lr = max(self.lr_min, self.optimizer.lr * self.lr_decay)

    def save(self, path: str) -> None:
        self.online.save(path)

    def load(self, path: str) -> None:
        self.online.load(path)
        self.target.copy_from(self.online)
