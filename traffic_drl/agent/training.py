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


def train_agent(env, agent, episodes: int, max_steps: int = None, log_path: str = None, verbose: bool = True):
    """Train any agent with act/update/decay_epsilon (QTableAgent or
    DQNAgent) for `episodes` episodes; returns the per-episode reward list
    and, if `log_path` is given, writes it as CSV (episode, reward,
    epsilon, loss) so the reward curve can be re-plotted from saved logs.
    `loss` is the mean DQN loss that episode (empty for the Q-table)."""
    rewards, epsilons, losses = [], [], []
    for ep in range(episodes):
        rewards.append(run_episode(env, agent, train=True, max_steps=max_steps))
        epsilons.append(agent.epsilon)
        losses.append(agent.pop_mean_loss() if hasattr(agent, "pop_mean_loss") else None)
        agent.decay_epsilon()
        if verbose:
            extra = f"states={len(agent.q)}" if hasattr(agent, "q") else f"loss={losses[-1]}"
            print(f"episode {ep + 1}/{episodes}  reward={rewards[-1]:.1f}  "
                  f"epsilon={epsilons[-1]:.3f}  {extra}")

    if log_path:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["episode", "reward", "epsilon", "loss"])
            for i, (r, e, l) in enumerate(zip(rewards, epsilons, losses), start=1):
                writer.writerow([i, r, e, "" if l is None else l])
    return rewards


train_qtable = train_agent  # Week 3 name, kept for compatibility
