"""Week 4 tests: the hand-written neural network on dummy data.
No SUMO or torch needed. Run with:
    python -m pytest tests/test_nn.py -v     (or: python tests/test_nn.py)
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traffic_drl.agent.nn import MLP, Adam, mse_loss  # noqa: E402


def test_forward_shape_and_single_sample():
    net = MLP([4, 8, 2])
    assert net.forward(np.zeros((5, 4))).shape == (5, 2)
    assert net.forward(np.zeros(4)).shape == (1, 2)


def test_same_seed_same_weights():
    a, b = MLP([3, 5, 2], seed=7), MLP([3, 5, 2], seed=7)
    assert all(np.array_equal(x, y) for x, y in zip(a.parameters(), b.parameters()))


def test_backprop_matches_numerical_gradient():
    """The key correctness check: analytic gradients == finite differences."""
    rng = np.random.default_rng(0)
    net = MLP([4, 6, 5, 3], seed=1, dtype=np.float64)
    x = rng.standard_normal((7, 4))
    target = rng.standard_normal((7, 3))
    mask = (rng.random((7, 3)) > 0.4).astype(np.float64)

    loss, grad = mse_loss(net.forward(x), target, mask)
    dW, db = net.backward(grad)
    analytic = [g for pair in zip(dW, db) for g in pair]

    eps = 1e-6
    for p, g in zip(net.parameters(), analytic):
        for idx in np.ndindex(p.shape):
            orig = p[idx]
            p[idx] = orig + eps
            up, _ = mse_loss(net.forward(x, cache=False), target, mask)
            p[idx] = orig - eps
            down, _ = mse_loss(net.forward(x, cache=False), target, mask)
            p[idx] = orig
            numeric = (up - down) / (2 * eps)
            assert abs(numeric - g[idx]) < 1e-5 * max(1.0, abs(numeric)), (idx, numeric, g[idx])


def test_mask_ignores_untaken_actions():
    pred = np.array([[1.0, 5.0]])
    target = np.array([[0.0, 0.0]])
    loss, grad = mse_loss(pred, target, mask=np.array([[1.0, 0.0]]))
    assert loss == 1.0 and grad[0, 1] == 0.0


def test_adam_fits_a_nonlinear_function():
    rng = np.random.default_rng(0)
    x = rng.uniform(-1, 1, (256, 2)).astype(np.float32)
    y = (np.sin(2 * x[:, :1]) + x[:, 1:] ** 2).astype(np.float32)
    net = MLP([2, 32, 32, 1], seed=0)
    opt = Adam(net, lr=1e-2)
    first = None
    for _ in range(600):
        loss, grad = mse_loss(net.forward(x), y)
        first = first if first is not None else loss
        opt.step(*net.backward(grad))
    assert loss < 0.05 * first and loss < 0.01, (first, loss)


def test_learns_xor():
    x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float32)
    y = np.array([[0], [1], [1], [0]], dtype=np.float32)
    net = MLP([2, 8, 1], seed=3)
    opt = Adam(net, lr=3e-2)
    for _ in range(800):
        _, grad = mse_loss(net.forward(x), y)
        opt.step(*net.backward(grad))
    assert np.all(np.abs(net.forward(x) - y) < 0.1)


def test_copy_from_is_independent():
    a, b = MLP([3, 4, 2], seed=0), MLP([3, 4, 2], seed=1)
    b.copy_from(a)
    x = np.ones((1, 3), dtype=np.float32)
    assert np.array_equal(a.forward(x), b.forward(x))
    a.W[0] += 1.0
    assert not np.array_equal(a.forward(x), b.forward(x))


def test_save_load_roundtrip():
    a, b = MLP([3, 4, 2], seed=0), MLP([3, 4, 2], seed=1)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "net.npz")
        a.save(path)
        b.load(path)
    x = np.ones((2, 3), dtype=np.float32)
    assert np.array_equal(a.forward(x), b.forward(x))


def test_load_rejects_wrong_architecture():
    a, b = MLP([3, 4, 2]), MLP([3, 5, 2])
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "net.npz")
        a.save(path)
        try:
            b.load(path)
        except ValueError:
            return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
