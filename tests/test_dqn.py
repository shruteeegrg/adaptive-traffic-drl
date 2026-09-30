"""Week 5 tests: replay buffer and DQN agent mechanics, plus a convergence
check on the simplified queue model. No SUMO needed.
    python -m pytest tests/test_dqn.py -v     (or: python tests/test_dqn.py)
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traffic_drl.agent import DQNAgent, ReplayBuffer, train_agent  # noqa: E402
from traffic_drl.agent.nn import huber_loss  # noqa: E402
from traffic_drl.env import SimpleQueueEnv  # noqa: E402


def _tiny_agent(**kw):
    params = dict(state_dim=2, hidden_sizes=(8,), batch_size=4, learn_start=4, target_sync_steps=10, seed=0)
    params.update(kw)
    return DQNAgent(**params)


def test_buffer_overwrites_oldest_when_full():
    buf = ReplayBuffer(3, 1)
    for i in range(5):
        buf.add([i], 0, float(i), [i + 1], False)
    assert len(buf) == 3
    assert sorted(buf.rewards.tolist()) == [2.0, 3.0, 4.0]


def test_buffer_sample_shapes_and_bounds():
    buf = ReplayBuffer(10, 2)
    for i in range(6):
        buf.add([i, i], i % 2, -1.0, [i, i], i == 5)
    s, a, r, s2, d = buf.sample(4)
    assert s.shape == (4, 2) and a.shape == (4,) and d.shape == (4,)
    try:
        buf.sample(7)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_huber_gradient_matches_numerical():
    rng = np.random.default_rng(0)
    pred, target = rng.standard_normal((5, 3)) * 3, rng.standard_normal((5, 3))
    mask = (rng.random((5, 3)) > 0.3).astype(float)
    _, grad = huber_loss(pred, target, mask)
    eps = 1e-6
    for idx in np.ndindex(pred.shape):
        up, down = pred.copy(), pred.copy()
        up[idx] += eps
        down[idx] -= eps
        numeric = (huber_loss(up, target, mask)[0] - huber_loss(down, target, mask)[0]) / (2 * eps)
        assert abs(numeric - grad[idx]) < 1e-6


def test_no_learning_before_learn_start():
    agent = _tiny_agent(learn_start=6)
    for _ in range(5):
        agent.update([1, 1], 0, -1.0, [1, 1], False)
    assert agent.learn_steps == 0
    agent.update([1, 1], 0, -1.0, [1, 1], False)
    assert agent.learn_steps == 1


def test_target_network_syncs_only_on_schedule():
    agent = _tiny_agent(target_sync_steps=10)
    for _ in range(9):
        agent.update([1, 1], 1, -1.0, [2, 2], False)
    assert any(not np.array_equal(o, t) for o, t in zip(agent.online.parameters(), agent.target.parameters()))
    agent.update([1, 1], 1, -1.0, [2, 2], False)  # 10th step -> sync
    assert all(np.array_equal(o, t) for o, t in zip(agent.online.parameters(), agent.target.parameters()))


def test_q_moves_toward_terminal_reward():
    """On a constant terminal transition the target is just the reward,
    so Q(s, a) must approach it (and the untaken action must not)."""
    agent = _tiny_agent(hidden_sizes=(16,), learning_rate=1e-2, learn_start=8, batch_size=8)
    s = np.array([0.5, 0.2], dtype=np.float32)
    before = agent.q_values(s).copy()
    for _ in range(400):
        agent.update(s, 0, -5.0, s, True)
    after = agent.q_values(s)
    assert abs(after[0] + 5.0) < 0.3, after
    assert abs(after[0] + 5.0) < abs(before[0] + 5.0)


def test_greedy_act_is_argmax_and_epsilon_decays():
    agent = _tiny_agent(epsilon_start=1.0, epsilon_end=0.1, epsilon_decay=0.5)
    s = np.array([0.3, 0.9], dtype=np.float32)
    best = int(np.argmax(agent.q_values(s)))
    assert all(agent.act(s, greedy=True) == best for _ in range(10))
    for _ in range(10):
        agent.decay_epsilon()
    assert agent.epsilon == 0.1


def test_save_load_roundtrip():
    a, b = _tiny_agent(seed=0), _tiny_agent(seed=1)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "dqn_final.pt")
        a.save(path)
        assert os.path.exists(path)  # exact path, no appended ".npz"
        b.load(path)
    s = np.array([0.1, 0.4], dtype=np.float32)
    assert np.array_equal(a.q_values(s), b.q_values(s))
    assert all(np.array_equal(o, t) for o, t in zip(b.online.parameters(), b.target.parameters()))


def test_training_is_reproducible():
    def run():
        env = SimpleQueueEnv(seed=0, state_scale=20, include_phase=True)
        agent = DQNAgent(4, hidden_sizes=(8,), learn_start=50, seed=0)
        return train_agent(env, agent, 3, max_steps=100, verbose=False)

    assert run() == run()


def _mean_eval(env, policy, episodes=10):
    totals = []
    for _ in range(episodes):
        state, total, done = env.reset(), 0.0, False
        while not done:
            state, r, done, _ = env.step(policy(state))
            total += r
        totals.append(total)
    return float(np.mean(totals))


def test_dqn_converges_and_beats_naive_policies():
    def make(seed):
        return SimpleQueueEnv(seed=seed, state_scale=20, include_phase=True)

    agent = DQNAgent(4, hidden_sizes=(32, 32), learning_rate=1e-3, epsilon_decay=0.95,
                     learn_start=300, target_sync_steps=200, seed=0)
    rewards = train_agent(make(0), agent, 150, verbose=False)
    assert np.mean(rewards[-10:]) > np.mean(rewards[:10])

    learned = _mean_eval(make(1000), lambda s: agent.act(s, greedy=True))
    always_ns = _mean_eval(make(1000), lambda s: 0)
    rng = np.random.default_rng(0)
    random_policy = _mean_eval(make(1000), lambda s: int(rng.integers(2)))
    print(f"learned={learned:.0f} always_ns={always_ns:.0f} random={random_policy:.0f}")
    assert learned > always_ns
    assert learned > random_policy


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
