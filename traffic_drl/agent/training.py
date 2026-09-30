"""Env-agnostic training/evaluation loops for the Q-table agent.

Works with anything exposing reset()/step(action)/close() -- `TraciEnv`
for real runs, `SimpleQueueEnv` for fast convergence checks -- so the
CLI stays a thin wrapper around this module.
"""

import csv
import os


def run_episode(env, agent, train: bool = True, max_steps: int = None) -> float:
    """Run one episode, returning the accumulated reward. With train=False
    the agent acts greedily and its table is left untouched."""
    state = env.reset()
    total = 0.0
    steps = 0
    while True:
        action = agent.act(state, greedy=not train)
        next_state, reward, done, _ = env.step(action)
        if train:
            agent.update(state, action, reward, next_state, done)
        total += reward
        state = next_state
        steps += 1
        if done or (max_steps is not None and steps >= max_steps):
            break
    return total


def train_qtable(env, agent, episodes: int, max_steps: int = None, log_path: str = None, verbose: bool = True):
    """Train for `episodes` episodes; returns the per-episode reward list
    and, if `log_path` is given, writes it as CSV (episode, reward,
    epsilon) so the reward curve can be re-plotted from saved logs."""
    rewards, epsilons = [], []
    for ep in range(episodes):
        rewards.append(run_episode(env, agent, train=True, max_steps=max_steps))
        epsilons.append(agent.epsilon)
        agent.decay_epsilon()
        if verbose:
            print(f"episode {ep + 1}/{episodes}  reward={rewards[-1]:.1f}  "
                  f"epsilon={epsilons[-1]:.3f}  states={len(agent.q)}")

    if log_path:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["episode", "reward", "epsilon"])
            for i, (r, e) in enumerate(zip(rewards, epsilons), start=1):
                writer.writerow([i, r, e])
    return rewards
