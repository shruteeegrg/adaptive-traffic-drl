"""Hand-written feed-forward neural network (Week 4), numpy only.

The proposal requires the DQN to be implemented from scratch, so this
module has no torch/autograd: forward pass, backpropagation, the Adam
optimizer and parameter copying (for the Week 5 target network) are all
written out explicitly. Correctness is established by a numerical
gradient check in tests/test_nn.py, not by trust.

Architecture: fully connected layers, ReLU on hidden layers, linear
output (Q-values are unbounded). Shapes: x is (batch, n_in).
"""

import numpy as np


class MLP:
    def __init__(self, sizes, seed: int = 0, dtype=np.float32):
        if len(sizes) < 2:
            raise ValueError("sizes needs at least input and output dimensions")
        self.sizes = list(sizes)
        self.dtype = dtype
        rng = np.random.default_rng(seed)
        # He initialization: variance 2/fan_in suits ReLU layers.
        self.W = [
            (rng.standard_normal((n_in, n_out)) * np.sqrt(2.0 / n_in)).astype(dtype)
            for n_in, n_out in zip(sizes[:-1], sizes[1:])
        ]
        self.b = [np.zeros(n_out, dtype=dtype) for n_out in sizes[1:]]
        self._cache = None

    @classmethod
    def from_config(cls, config: dict, n_in: int, n_out: int) -> "MLP":
        params = config.get("dqn", {})
        return cls([n_in, *params.get("hidden_sizes", [64, 64]), n_out], seed=params.get("seed", 0))

    # -- forward / backward -------------------------------------------------

    def forward(self, x, cache: bool = True) -> np.ndarray:
        a = np.asarray(x, dtype=self.dtype)
        if a.ndim == 1:
            a = a[None, :]
        activations = [a]
        last = len(self.W) - 1
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = a @ W + b
            a = z if i == last else np.maximum(z, 0.0)
            activations.append(a)
        if cache:
            self._cache = activations
        return a

    def backward(self, grad_out: np.ndarray):
        """Backpropagate dLoss/dOutput (batch, n_out) from the last
        forward(); returns (dW list, db list) matching self.W / self.b."""
        if self._cache is None:
            raise RuntimeError("call forward() before backward()")
        acts = self._cache
        dW, db = [None] * len(self.W), [None] * len(self.b)
        delta = np.asarray(grad_out, dtype=self.dtype)
        for i in reversed(range(len(self.W))):
            dW[i] = acts[i].T @ delta
            db[i] = delta.sum(axis=0)
            if i > 0:
                delta = (delta @ self.W[i].T) * (acts[i] > 0)  # ReLU gate
        return dW, db

    # -- parameters ---------------------------------------------------------

    def parameters(self):
        """Flat list of parameter arrays (live references, W0, b0, W1, b1...)."""
        return [p for pair in zip(self.W, self.b) for p in pair]

    def soft_update(self, other: "MLP", tau: float) -> None:
        """Move this net's weights a fraction `tau` toward another net's (Polyak averaging):
        a smoother alternative to the hard copy for the DQN target network."""
        for mine, theirs in zip(self.parameters(), other.parameters()):
            mine[...] = (1.0 - tau) * mine + tau * theirs

    def copy_from(self, other: "MLP") -> None:
        """Hard-copy another net's weights (DQN target-network sync)."""
        for mine, theirs in zip(self.parameters(), other.parameters()):
            mine[...] = theirs

    def save(self, path: str) -> None:
        with open(path, "wb") as f:  # file object: np.savez would append ".npz" to a bare path
            np.savez(f, sizes=np.array(self.sizes), **{f"p{i}": p for i, p in enumerate(self.parameters())})

    def load(self, path: str) -> None:
        data = np.load(path)
        if list(data["sizes"]) != self.sizes:
            raise ValueError(f"checkpoint sizes {list(data['sizes'])} != network sizes {self.sizes}")
        for i, p in enumerate(self.parameters()):
            p[...] = data[f"p{i}"]


def mse_loss(pred: np.ndarray, target: np.ndarray, mask: np.ndarray = None):
    """Mean squared error over the batch and its gradient wrt pred.

    `mask` (same shape, 1 where the error counts) restricts the loss to
    the action actually taken, as DQN requires: only Q(s, a_taken) has a
    target."""
    diff = pred - target
    if mask is not None:
        diff = diff * mask
    batch = pred.shape[0]
    loss = float(np.sum(diff ** 2) / batch)
    grad = 2.0 * diff / batch
    return loss, grad


def huber_loss(pred: np.ndarray, target: np.ndarray, mask: np.ndarray = None, delta: float = 1.0):
    """Huber loss (quadratic near zero, linear beyond `delta`) and its
    gradient wrt pred. The standard DQN loss: large TD errors early in
    training give bounded gradients instead of exploding ones."""
    diff = pred - target
    if mask is not None:
        diff = diff * mask
    batch = pred.shape[0]
    small = np.abs(diff) <= delta
    loss = float(np.sum(np.where(small, 0.5 * diff ** 2, delta * (np.abs(diff) - 0.5 * delta))) / batch)
    grad = np.where(small, diff, delta * np.sign(diff)) / batch
    return loss, grad


class Adam:
    def __init__(self, net: MLP, lr: float = 1e-3, beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
        self.net, self.lr, self.beta1, self.beta2, self.eps = net, lr, beta1, beta2, eps
        self.m = [np.zeros_like(p) for p in net.parameters()]
        self.v = [np.zeros_like(p) for p in net.parameters()]
        self.t = 0

    def step(self, dW, db) -> None:
        grads = [g for pair in zip(dW, db) for g in pair]
        self.t += 1
        for p, g, m, v in zip(self.net.parameters(), grads, self.m, self.v):
            m[...] = self.beta1 * m + (1 - self.beta1) * g
            v[...] = self.beta2 * v + (1 - self.beta2) * g * g
            m_hat = m / (1 - self.beta1 ** self.t)
            v_hat = v / (1 - self.beta2 ** self.t)
            p -= (self.lr * m_hat / (np.sqrt(v_hat) + self.eps)).astype(p.dtype)
