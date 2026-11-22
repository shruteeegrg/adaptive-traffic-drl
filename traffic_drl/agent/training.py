"""Env-agnostic training/evaluation loops for the Q-table and DQN agents.

Works with anything exposing reset()/step(action)/close() -- `TraciEnv`
for real runs, `SimpleQueueEnv` for fast convergence checks -- so the
CLI stays a thin wrapper around this module.
"""

import csv
import math
import os


def bootstrap_done(agent, done: bool, info: dict) -> bool:
    """The `done` flag to store for learning. A time-limit cut-off (info["truncated"]) is not a real terminal
    state; agents that set `bootstrap_on_timeout` keep bootstrapping from it. Default: unchanged behaviour."""
    if done and (info or {}).get("truncated") and getattr(agent, "bootstrap_on_timeout", False):
        return False
    return done


def run_episode(env, agent, train: bool = True, max_steps: int = None) -> float:
    """Run one episode, returning the accumulated reward. With train=False
    the agent acts greedily and its table is left untouched."""
    state = env.reset()
    total = 0.0
    steps = 0
    while True:
        action = agent.act(state, greedy=not train)
        next_state, reward, done, info = env.step(action)
        if train:
            agent.update(state, action, reward, next_state, bootstrap_done(agent, done, info))
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


def pretrain_from_teacher(env, agent, teacher, episodes: int, noise: float = 0.2, offline_steps: int = 0,
                          epsilon_after: float = 0.1, max_steps: int = None, seed: int = 0, verbose: bool = False):
    """Seed the DQN with a teacher controller's experience (Q-learning is off-policy, so it can learn from
    anyone's transitions). The teacher drives `episodes` episodes, with a fraction `noise` of random actions so
    the buffer also holds the consequences of poor choices; every transition goes through agent.update, then
    `offline_steps` extra gradient steps fit the buffer. Exploration is then set to `epsilon_after`, ready for
    ordinary training to improve on the teacher."""
    import numpy as _np

    rng = _np.random.default_rng(seed)
    for ep in range(episodes):
        state = env.reset()
        if hasattr(teacher, "reset"):
            teacher.reset()
        steps = 0
        while True:
            explore = rng.random() < noise
            action = int(rng.integers(agent.n_actions)) if explore else teacher.act(state, greedy=True)
            next_state, reward, done, info = env.step(action)
            stored_done = bootstrap_done(agent, done, info)
            if getattr(agent, "demo_fraction", 0.0) > 0 and hasattr(agent, "add_demo"):
                agent.add_demo(state, action, reward, next_state, stored_done, expert=not explore)
            agent.update(state, action, reward, next_state, stored_done)
            state = next_state
            steps += 1
            if done or (max_steps and steps >= max_steps):
                break
        if verbose:
            print(f"  teacher episode {ep + 1}/{episodes}: {steps} transitions")
    if offline_steps:
        agent.offline_learn(offline_steps)
    agent.epsilon = epsilon_after
    return agent


def maybe_pretrain(env, agent, config: dict, verbose: bool = False, make_teacher=None) -> bool:
    """Run the `dqn.pretrain` section of the config, if any. Returns True when a teacher was used.

        pretrain: {teacher: {min: 10, max: 40, ratio: 4, gap: 0}, episodes: 20, noise: 0.2,
                   offline_steps: 3000, epsilon_after: 0.1}
    """
    spec = config.get("dqn", {}).get("pretrain")
    if not spec:
        return False
    if make_teacher is None:
        from traffic_drl.baseline import DensityActuatedAgent

        t = spec.get("teacher", {})
        make_teacher = lambda: DensityActuatedAgent.from_config(   # noqa: E731
            config, min_green=t.get("min", 10), max_green=t.get("max", 40),
            ratio=t.get("ratio", 4), gap_queue=t.get("gap", 0)).attach(env)
    pretrain_from_teacher(env, agent, make_teacher(), episodes=spec.get("episodes", 20), noise=spec.get("noise", 0.2),
                          offline_steps=spec.get("offline_steps", 0), epsilon_after=spec.get("epsilon_after", 0.1),
                          seed=config.get("dqn", {}).get("seed", 0), verbose=verbose)
    return True


def train_agent(env, agent, episodes: int, max_steps: int = None, log_path: str = None, verbose: bool = True,
                eval_every: int = None, eval_episodes: int = 2, best_path: str = None, history: dict = None,
                eval_at_start: bool = False, on_episode=None):
    """Train any agent with act/update/decay_epsilon (QTableAgent or
    DQNAgent) for `episodes` episodes; returns the per-episode reward list
    and, if `log_path` is given, writes it as CSV (episode, reward,
    epsilon, loss, plus per-second mean_queue / avg_wait_per_vehicle /
    throughput_per_hour when the env measures them) so the reward curve can be re-plotted from saved logs.
    `loss` is the mean DQN loss that episode (empty for the Q-table).

    With `eval_every`, the greedy policy is evaluated on unseen seeds every
    that-many episodes (and after the last); if `best_path` is given the
    best-scoring agent so far is saved there. `history`, if a dict, is
    filled with best_score / best_episode / evals.

    `on_episode`, if given, is called after every episode with {episode, episodes, reward, epsilon, loss,
    metrics, eval (that episode's evaluation or None), best_episode}; returning True stops training early
    (a background job uses it to report progress and to honour a cancel request)."""
    best_score, best_episode, evals = float("-inf"), None, []
    rewards, epsilons, losses, metrics = [], [], [], []
    if eval_at_start and eval_every:        # e.g. the policy just distilled from a teacher: a candidate "best" too
        result = evaluate(env, agent, eval_episodes, max_steps=max_steps)
        evals.append({"episode": 0, **result})
        best_score, best_episode = _score(result), 0
        if best_path:
            os.makedirs(os.path.dirname(best_path) or ".", exist_ok=True)
            agent.save(best_path)
        if verbose:
            print("  eval @ episode 0: " + "  ".join(f"{k}={v:.2f}" for k, v in result.items() if "/" not in k))
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
        if on_episode is not None:
            just_evaluated = evals[-1] if evals and evals[-1]["episode"] == ep + 1 else None
            if on_episode({"episode": ep + 1, "episodes": episodes, "reward": rewards[-1], "epsilon": epsilons[-1],
                           "loss": losses[-1], "metrics": metrics[-1], "eval": just_evaluated,
                           "best_episode": best_episode}):
                break

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
