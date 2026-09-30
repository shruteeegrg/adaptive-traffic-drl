# Week 3 Log — Baseline Q-table Agent

**Date submitted:** 2026-09-30
**Branch / PR:** `week-03-qtable-baseline`

## Accomplished last week (Week 2)

- Built the single 4-arm SUMO intersection (`configs/intersection.net.xml`)
  and generated base / `rush_hour` / `low_traffic` route files via scripts.
- Implemented the config-driven `TraciEnv` (`reset()` / `step(action)`,
  queue-length state, automatic yellow clearance) and a smoke test +
  `traffic-drl env-check`.
- Added `docs/architecture.md` (layered architecture diagram). Both Week 2
  PRs merged into `main`.

## This week (Week 3)

- [x] Implemented the tabular Q-learning agent from scratch
  (`traffic_drl/agent/q_table_agent.py`, numpy only): queue lengths are
  discretized into 4 buckets per approach, epsilon-greedy with per-episode
  decay, standard Bellman update (no bootstrapping on terminal steps),
  JSON save/load. Hyperparameters live in the `qtable:` section of
  `configs/intersection.yaml`.
- [x] Env-agnostic training/eval loops (`traffic_drl/agent/training.py`)
  that write a per-episode reward CSV (episode, reward, epsilon).
- [x] Added `SimpleQueueEnv` (`traffic_drl/env/toy_env.py`), a seeded
  pure-Python two-direction queue model with the same `reset()`/`step()`
  contract as `TraciEnv`. It is the "simplified problem" used to check
  convergence quickly and deterministically without a SUMO process.
- [x] Wired `traffic-drl train --agent qtable --config ...` (flags:
  `--env {sumo,toy}`, `--episodes`, `--out-dir`). It saves
  `qtable.json`, `qtable_rewards.csv` and `qtable_reward_curve.png`.
- [x] `traffic_drl/viz`: `plot_reward_curve` (reads the saved CSV; Week 7
  extends this into the full dashboard).
- [x] `tests/test_qtable.py` (9 tests). Convergence test: after 80 training
  episodes on the toy model, the greedy policy on *unseen* episodes scores
  about -2200 mean reward vs about -5800 for always-NS and about -3000 for a
  random policy.

## Planned for next week (Week 4)

- [ ] Full-intersection state/action/reward design (richer than queue
  length only: waiting time, current phase), with config-driven settings.
- [ ] Hand-written neural network (forward + backprop), unit-tested on
  dummy data, including a numerical gradient check.
- [ ] Run the Q-table through `TraciEnv` on a machine with SUMO installed
  and record its real-intersection baseline reward curve.

## Blockers / risks

- **Not yet verified against real SUMO this week.** SUMO is not installed
  on the machine used this week, so Q-table training was verified on
  `SimpleQueueEnv` only. `traffic-drl train --agent qtable --env sumo` uses
  the same agent and loop but has not been run. Needs a SUMO run before the
  Week 3 criterion "Q-table converges" is fully closed for the real network.
- The state has no current-phase information, so the table is not strictly
  Markov; acceptable for a baseline, and Week 4's state design addresses it.
- The reward curve is noisy (each episode draws a new arrival stream, plus
  exploration); judge learning by the held-out evaluation, not one episode.

## Commits this period

- see `git log week-03-qtable-baseline`
