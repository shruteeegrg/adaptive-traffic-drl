"""Env-agnostic training/evaluation loops for the Q-table agent.

Works with anything exposing reset()/step(action)/close() -- `TraciEnv`
for real runs, `SimpleQueueEnv` for fast convergence checks -- so the
CLI stays a thin wrapper around this module.
"""

import csv
import math
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


EVAL_SEED_BASE = 10_000  # SUMO seeds for evaluation, far from the training seeds


def _aggregate(per_scenario: dict) -> dict:
    """Combine per-scenario results into one dict. Means for every metric,
    except mean_total_waiting, which uses exp(mean(log1p(.))) - 1 so that a
    relative change counts the same in light and heavy traffic (1.5 -> 25
    matters as much as 140 -> 200). Per-scenario values are kept under
    "<scenario>/<metric>"."""
    names = list(per_scenario)
    out = {}
    for key in per_scenario[names[0]]:
        vals = [per_scenario[n][key] for n in names]
        out[key] = (math.expm1(sum(math.log1p(v) for v in vals) / len(vals))
                    if key == "mean_total_waiting" else sum(vals) / len(vals))
    for n in names:
        for key in ("mean_total_waiting", "throughput_per_hour", "switches"):
            if key in per_scenario[n]:
                out[f"{n}/{key}"] = per_scenario[n][key]
    return out


def evaluate(env, agent, episodes: int = 2, max_steps: int = None, seed_base: int = EVAL_SEED_BASE) -> dict:
    """Greedy (no exploration, no learning) evaluation, averaged over
    `episodes`. Returns {"reward": ...} plus mean_queue /
    avg_wait_per_vehicle / throughput_per_hour when the env measures them.
    On envs with a `seed_base` (TraciEnv) it runs on unseen SUMO seeds.
    On a mixed-scenario env it evaluates each scenario (`episodes` each) and
    aggregates (see _aggregate)."""
    names = getattr(env, "scenario_names", None) or []
    if len(names) <= 1:
        return _evaluate_one(env, agent, episodes, max_steps, seed_base)
    per_scenario = {}
    try:
        for i, name in enumerate(names):
            if name in per_scenario:         # a scenario listed twice (over-sampled in training) is scored once
                continue
            env.force_scenario = i
            per_scenario[name] = _evaluate_one(env, agent, episodes, max_steps, seed_base)
    finally:
        env.force_scenario = None
    return _aggregate(per_scenario)


def _evaluate_one(env, agent, episodes: int, max_steps, seed_base) -> dict:
    saved = getattr(env, "seed_base", None)
    if saved is not None:
        env.seed_base = seed_base
    try:
        rows = []
        for _ in range(episodes):
            reward = run_episode(env, agent, train=False, max_steps=max_steps)
            rows.append({"reward": reward, **(env.metrics() if hasattr(env, "metrics") else {})})
    finally:
        if saved is not None:
            env.seed_base = saved
    return {k: float(sum(r[k] for r in rows) / len(rows)) for k in rows[0]}


def _score(result: dict) -> float:
    """Higher is better. Prefer mean_total_waiting (halted + not-yet-inserted
    vehicles, per simulated second: comparable across policies and valid
    under overload); fall back to reward where the env has no metrics."""
    return -result["mean_total_waiting"] if "mean_total_waiting" in result else result["reward"]


def train_agent(env, agent, episodes: int, max_steps: int = None, log_path: str = None, verbose: bool = True,
                eval_every: int = None, eval_episodes: int = 2, best_path: str = None, history: dict = None):
    """Train any agent with act/update/decay_epsilon (QTableAgent or
    DQNAgent) for `episodes` episodes; returns the per-episode reward list
    and, if `log_path` is given, writes it as CSV (episode, reward,
    epsilon, loss, plus per-second mean_queue / avg_wait_per_vehicle /
    throughput_per_hour when the env measures them) so the reward curve can be re-plotted from saved logs.
    `loss` is the mean DQN loss that episode (empty for the Q-table).

    With `eval_every`, the greedy policy is evaluated on unseen seeds every
    that-many episodes (and after the last); if `best_path` is given the
    best-scoring agent so far is saved there. `history`, if a dict, is
    filled with best_score / best_episode / evals."""
    best_score, best_episode, evals = float("-inf"), None, []
    rewards, epsilons, losses, metrics = [], [], [], []
    for ep in range(episodes):
        rewards.append(run_episode(env, agent, train=True, max_steps=max_steps))
        epsilons.append(agent.epsilon)
        metrics.append(env.metrics() if hasattr(env, "metrics") else {})
        losses.append(agent.pop_mean_loss() if hasattr(agent, "pop_mean_loss") else None)
        agent.decay_epsilon()
        if eval_every and ((ep + 1) % eval_every == 0 or ep + 1 == episodes):
            result = evaluate(env, agent, eval_episodes, max_steps=max_steps)
            evals.append({"episode": ep + 1, **result})
            if _score(result) > best_score:
                best_score, best_episode = _score(result), ep + 1
                if best_path:
                    os.makedirs(os.path.dirname(best_path) or ".", exist_ok=True)
                    agent.save(best_path)
            if verbose:
                shown = {k: v for k, v in result.items() if "/" not in k}
                per = "  ".join(f"[{k.split('/')[0]}] wait={v:.1f}" for k, v in result.items()
                                if k.endswith("/mean_total_waiting"))
                print(f"  eval @ episode {ep + 1}: " + "  ".join(f"{k}={v:.2f}" for k, v in shown.items())
                      + (f"  | {per}" if per else "")
                      + (f"  (best so far: episode {best_episode})" if best_episode else ""))
        if verbose:
            extra = f"states={len(agent.q)}" if hasattr(agent, "q") else f"loss={losses[-1]}"
            print(f"episode {ep + 1}/{episodes}  reward={rewards[-1]:.1f}  "
                  f"epsilon={epsilons[-1]:.3f}  {extra}")

    if log_path:
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        with open(log_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["episode", "reward", "epsilon", "loss",
                             "mean_queue", "mean_backlog", "mean_total_waiting",
                             "avg_wait_per_vehicle", "throughput_per_hour",
                             "switches", "ns_green_fraction"])
            for i, (r, e, l, m) in enumerate(zip(rewards, epsilons, losses, metrics), start=1):
                writer.writerow([i, r, e, "" if l is None else l,
                                 m.get("mean_queue", ""), m.get("mean_backlog", ""),
                                 m.get("mean_total_waiting", ""), m.get("avg_wait_per_vehicle", ""),
                                 m.get("throughput_per_hour", ""),
                                 m.get("switches", ""), m.get("ns_green_fraction", "")])
    if history is not None:
        history.update(best_score=best_score, best_episode=best_episode, evals=evals)
    return rewards


train_qtable = train_agent  # Week 3 name, kept for compatibility
