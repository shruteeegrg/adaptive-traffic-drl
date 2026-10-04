"""Week 3 tests: Q-table agent logic and convergence on the simplified
queue model. No SUMO needed. Run with:
    python -m pytest tests/test_qtable.py -v     (or: python tests/test_qtable.py)
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from traffic_drl.agent import QTableAgent, run_episode, train_qtable  # noqa: E402
from traffic_drl.baseline import FixedTimeAgent  # noqa: E402
from traffic_drl.env import SimpleQueueEnv  # noqa: E402


def test_discretize_buckets():
    agent = QTableAgent(queue_bins=(1, 4, 8))
    assert agent.discretize([0, 1, 5, 20]) == (0, 1, 2, 3)


def test_update_moves_q_toward_target():
    agent = QTableAgent(alpha=0.5, gamma=0.9)
    s, s2 = [0, 0], [5, 5]
    agent.update(s, 1, reward=-2.0, next_state=s2, done=True)
    assert agent.q[agent.discretize(s)][1] == -1.0  # 0 + 0.5 * (-2 - 0)


def test_done_does_not_bootstrap():
    agent = QTableAgent(alpha=1.0, gamma=0.9)
    agent._row(agent.discretize([5, 5]))[:] = 100.0
    agent.update([0, 0], 0, reward=1.0, next_state=[5, 5], done=True)
    assert agent.q[agent.discretize([0, 0])][0] == 1.0


def test_greedy_picks_best_action():
    agent = QTableAgent()
    agent._row(agent.discretize([0, 0]))[:] = [-3.0, -1.0]
    assert all(agent.act([0, 0], greedy=True) == 1 for _ in range(20))


def test_epsilon_decays_to_floor():
    agent = QTableAgent(epsilon_start=1.0, epsilon_end=0.1, epsilon_decay=0.5)
    for _ in range(10):
        agent.decay_epsilon()
    assert agent.epsilon == 0.1


def test_save_load_roundtrip():
    agent = QTableAgent()
    agent.update([3, 0], 1, -4.0, [2, 0], False)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "q.json")
        agent.save(path)
        other = QTableAgent()
        other.load(path)
    assert other.q.keys() == agent.q.keys()
    for k in agent.q:
        assert np.allclose(other.q[k], agent.q[k])


def test_toy_env_is_repeatable():
    def rollout():
        env = SimpleQueueEnv(seed=3)
        env.reset()
        return [env.step(i // 10 % 2)[1] for i in range(60)]

    assert rollout() == rollout()


def _mean_eval(env, policy, episodes=10):
    totals = []
    for _ in range(episodes):
        state, total, done = env.reset(), 0.0, False
        while not done:
            state, r, done, _ = env.step(policy(state))
            total += r
        totals.append(total)
    return float(np.mean(totals))


def test_qtable_converges_and_beats_naive_policies():
    def make(seed):
        return SimpleQueueEnv(seed=seed, include_phase=True)  # phase in the state: needed to learn

    agent = QTableAgent(epsilon_decay=0.92, seed=0)
    rewards = train_qtable(make(0), agent, episodes=150, verbose=False)
    assert np.mean(rewards[-10:]) > np.mean(rewards[:10])

    # Evaluate on unseen episodes (different seed), greedy, no updates.
    learned = _mean_eval(make(1000), lambda s: agent.act(s, greedy=True))
    always_ns = _mean_eval(make(1000), lambda s: 0)
    rng = np.random.default_rng(0)
    random_policy = _mean_eval(make(1000), lambda s: int(rng.integers(2)))
    timer = FixedTimeAgent(green_steps=15)
    fixed = _mean_eval(make(1000), lambda s: timer.act())
    print(f"learned={learned:.0f} always_ns={always_ns:.0f} random={random_policy:.0f} fixed15={fixed:.0f}")
    assert learned > always_ns
    assert learned > random_policy
    assert learned > fixed


def test_run_episode_eval_does_not_modify_table():
    agent = QTableAgent()
    run_episode(SimpleQueueEnv(seed=0), agent, train=True, max_steps=20)
    snapshot = {k: v.copy() for k, v in agent.q.items()}
    run_episode(SimpleQueueEnv(seed=5), agent, train=False, max_steps=20)
    for k, v in snapshot.items():
        assert np.array_equal(agent.q[k], v)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
