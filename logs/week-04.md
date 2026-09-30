# Week 4 Log — State/Reward Design + Neural Network

**Date submitted:** 2026-09-30
**Branch / PR:** pushed directly to `main`

## Accomplished last week (Week 3)

- Tabular Q-learning agent (`traffic_drl/agent/q_table_agent.py`), env-agnostic
  training loop, `SimpleQueueEnv` toy model, `traffic-drl train --agent qtable`,
  reward-curve plot, 9 tests. On the toy model the learned policy beat
  always-NS and random on unseen episodes.
- **Open item:** not yet run against real SUMO (no SUMO on that machine).

## This week (Week 4)

- [x] Config-driven state/reward design (`traffic_drl/env/features.py`):
  state features `queue`, `waiting_time`, `phase` (one-hot), `phase_elapsed`,
  each scaled; reward = -(queue_weight*queue + wait_weight*waiting time)
  - switch_penalty, / reward_scale. Pure functions, unit-tested without SUMO.
  Defaults reproduce the Week 2 behaviour exactly, so the Q-table is unaffected.
- [x] `TraciEnv` builds state/reward through that module and exposes
  `state_size`; tracks current phase and time-in-phase.
- [x] Config inheritance (`extends:` in `traffic_drl/config.py`) and
  `configs/dqn.yaml`: the full 11-input design (4 queue, 4 waiting time,
  2 phase, 1 time-in-phase) plus network settings, overriding only what
  differs from `intersection.yaml`.
- [x] Hand-written MLP (`traffic_drl/agent/nn.py`): forward, backprop, masked
  MSE loss, Adam, `copy_from` (for the Week 5 target net), save/load. No torch.
- [x] `tests/test_nn.py` (9 tests) incl. a numerical gradient check of
  backprop and fitting sin/quadratic data and XOR; `tests/test_state_reward.py`
  (8 tests) incl. `TraciEnv` wiring against a fake `traci`.

## Planned for next week (Week 5)

- [ ] DQN agent: replay buffer, target network (hard sync), epsilon-greedy,
  Bellman-target training step using `MLP` + `Adam`.
- [ ] Wire `traffic-drl train --agent dqn --config configs/dqn.yaml`.
- [ ] Run the Q-table and `env-check` on real SUMO (Windows laptop) and record results.

## Blockers / risks

- The new `TraciEnv` state/reward path is tested against a fake `traci`, not
  real SUMO. Run `tests/test_env_smoke.py` and `traffic-drl env-check` once
  SUMO is installed to confirm nothing regressed.
- `getWaitingTime` is read per edge each step (two TraCI reads per edge per
  step with waiting time enabled); fine now, revisit if training is slow.
- Scales/weights in `dqn.yaml` are reasoned guesses, to be tuned in Week 6.

## Commits this period

- see `git log` on `main` (Week 4 commits)
