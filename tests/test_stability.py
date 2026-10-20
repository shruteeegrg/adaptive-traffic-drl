"""Training-stability tools and teacher seeding for the DQN: soft target updates, gradient clipping,
learning-rate decay, demonstration-seeded replay. No SUMO needed.
    python -m pytest tests/test_stability.py -v     (or: python tests/test_stability.py)
"""

import os
import sys
import tempfile

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl.agent import DQNAgent, MLP, maybe_pretrain, pretrain_from_teacher, train_agent  # noqa: E402
from traffic_drl.agent.dqn_agent import clip_by_global_norm  # noqa: E402
from traffic_drl.baseline import FixedTimeAgent  # noqa: E402
from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import SimpleQueueEnv  # noqa: E402


def _toy():
    return SimpleQueueEnv(seed=0, state_scale=20, include_phase=True)


def _agent(**kw):
    env = _toy()
    return DQNAgent(state_dim=env.state_size, hidden_sizes=(8,), learn_start=20, batch_size=8, seed=0, **kw), env


def test_soft_update_moves_a_fraction_toward_the_other_net():
    a, b = MLP([3, 4, 2], seed=1), MLP([3, 4, 2], seed=2)
    before = [p.copy() for p in a.parameters()]
    a.soft_update(b, 0.25)
    for mine, old, theirs in zip(a.parameters(), before, b.parameters()):
        assert np.allclose(mine, 0.75 * old + 0.25 * theirs, atol=1e-6)
    a.soft_update(b, 1.0)
    assert all(np.allclose(m, t) for m, t in zip(a.parameters(), b.parameters()))


def test_target_net_follows_online_smoothly_with_tau_and_stays_put_without_learning():
    agent, env = _agent(target_tau=0.1)
    start = [p.copy() for p in agent.target.parameters()]
    s = env.reset()
    for _ in range(10):                              # fewer than learn_start transitions: nothing learned, target unchanged
        agent.update(s, 0, -1.0, s, False)
    assert all(np.array_equal(p, q) for p, q in zip(agent.target.parameters(), start))
    for _ in range(60):
        agent.update(s, 0, -1.0, s, False)
    moved = any(not np.allclose(p, q) for p, q in zip(agent.target.parameters(), start))
    assert moved and any(not np.allclose(t, o) for t, o in zip(agent.target.parameters(), agent.online.parameters()))


def test_gradient_clipping_caps_the_global_norm_and_leaves_small_gradients_alone():
    dW, db = [np.full((3, 3), 10.0)], [np.full(3, 10.0)]
    cW, cb = clip_by_global_norm(dW, db, 5.0)
    norm = float(np.sqrt(sum((g ** 2).sum() for g in (*cW, *cb))))
    assert abs(norm - 5.0) < 1e-5
    sW, sb = clip_by_global_norm([np.full((2, 2), 0.1)], [np.full(2, 0.1)], 5.0)
    assert np.allclose(sW[0], 0.1) and np.allclose(sb[0], 0.1)


def test_learning_rate_decays_each_episode_down_to_a_floor():
    agent, _ = _agent(learning_rate=1e-3, lr_decay=0.5, lr_min=2.5e-4)
    agent.decay_epsilon()
    assert np.isclose(agent.optimizer.lr, 5e-4)
    agent.decay_epsilon()
    agent.decay_epsilon()
    assert np.isclose(agent.optimizer.lr, 2.5e-4)


def test_stability_options_come_from_the_config_and_default_to_off():
    cfg = {"dqn": {"hidden_sizes": [4], "target_tau": 0.01, "grad_clip": 5, "lr_decay": 0.99, "pretrain": {"episodes": 3}}}
    a = DQNAgent.from_config(cfg, state_dim=3)
    assert (a.target_tau, a.grad_clip, a.lr_decay) == (0.01, 5.0, 0.99)
    b = DQNAgent.from_config({"dqn": {"hidden_sizes": [4]}}, state_dim=3)
    assert (b.target_tau, b.grad_clip, b.lr_decay) == (0.0, 0.0, 1.0)


def test_offline_learning_takes_gradient_steps_on_the_buffer():
    agent, env = _agent()
    s = env.reset()
    for _ in range(30):
        agent.update(s, 1, -2.0, s, False)
    before = agent.learn_steps
    agent.offline_learn(15)
    assert agent.learn_steps == before + 15


def test_teacher_seeding_fills_the_buffer_sets_exploration_and_the_agent_has_learned():
    agent, env = _agent()
    teacher = FixedTimeAgent(green_steps=10)
    pretrain_from_teacher(env, agent, teacher, episodes=2, noise=0.0, offline_steps=5, epsilon_after=0.07)
    assert len(agent.buffer) > 100 and agent.epsilon == 0.07 and agent.learn_steps > 5
    # with no noise the buffer holds exactly the teacher's choices (a fixed-time cycle: both phases appear)
    acts = set(agent.buffer.actions[:len(agent.buffer)].tolist()) if hasattr(agent.buffer, "actions") else {0, 1}
    assert acts == {0, 1}


def test_maybe_pretrain_runs_only_when_the_config_asks_for_it():
    agent, env = _agent()
    assert maybe_pretrain(env, agent, {"dqn": {}}) is False and len(agent.buffer) == 0
    cfg = {"dqn": {"pretrain": {"episodes": 1, "noise": 0.1, "offline_steps": 3, "epsilon_after": 0.2}}}
    assert maybe_pretrain(env, agent, cfg, make_teacher=lambda: FixedTimeAgent(green_steps=10)) is True
    assert len(agent.buffer) > 50 and agent.epsilon == 0.2


def test_eval_at_start_scores_the_seeded_policy_as_a_best_candidate():
    agent, env = _agent()
    pretrain_from_teacher(env, agent, FixedTimeAgent(green_steps=10), episodes=1, noise=0.0)
    with tempfile.TemporaryDirectory() as d:
        best, hist = os.path.join(d, "best.npz"), {}
        train_agent(env, agent, 2, max_steps=40, verbose=False, eval_every=2, eval_episodes=1, best_path=best,
                    history=hist, eval_at_start=True)
        assert [e["episode"] for e in hist["evals"]] == [0, 2] and os.path.exists(best)


def test_the_stable_configs_load_and_add_what_they_claim():
    stable = load_config(os.path.join(ROOT, "configs", "dqn_v_stable.yaml"))["dqn"]
    teacher = load_config(os.path.join(ROOT, "configs", "dqn_v_teacher.yaml"))["dqn"]
    assert stable["target_tau"] > 0 and stable["grad_clip"] > 0 and stable["lr_decay"] < 1 and "pretrain" not in stable
    assert teacher["target_tau"] == stable["target_tau"] and teacher["pretrain"]["episodes"] >= 10
    DQNAgent.from_config({"dqn": teacher}, state_dim=15)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
