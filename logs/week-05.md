# Week 5 Log — DQN Training Loop

**Date submitted:** 2026-09-30
**Branch / PR:** pushed directly to `main`

## Accomplished last week (Week 4)

- Config-driven state/reward design (`traffic_drl/env/features.py`), config
  inheritance (`extends:`) and `configs/dqn.yaml`; hand-written MLP with
  backprop + Adam, verified by a numerical gradient check; 17 new tests.
- **Open item:** `TraciEnv` changes tested against a fake `traci` only.

## This week (Week 5)

- [x] `ReplayBuffer` (`traffic_drl/agent/replay_buffer.py`): ring buffer, uniform sampling.
- [x] `DQNAgent` (`traffic_drl/agent/dqn_agent.py`): online + target network
  (hard sync every `target_sync_steps`), epsilon-greedy with per-episode decay,
  Bellman target from the target net (no bootstrap on terminal steps), loss
  applied only to the action taken, Huber (default) or MSE loss, Adam.
  Same `act`/`update`/`decay_epsilon` interface as the Q-table, so one
  training loop drives both.
- [x] `huber_loss` added to `nn.py`; `np.savez` path bug avoided (saves to the exact path).
- [x] `train_qtable` generalised to `train_agent`; reward CSV gains a per-episode `loss` column.
- [x] `traffic-drl train --agent dqn --config configs/dqn.yaml` wired (flags
  `--env {sumo,toy}`, `--episodes`, `--out-dir`); saves `dqn.npz`, CSV, reward plot.
- [x] `tests/test_dqn.py` (10 tests): buffer wraparound/sampling, Huber gradient
  check, no learning before `learn_start`, target sync schedule, Q moving to a
  known terminal reward, save/load, reproducibility, and convergence.

## Results (toy queue model, not SUMO)

Held-out episodes, greedy policy, mean reward (higher is better):
DQN about -2400 (150 episodes), Q-table about -2200, random about -3000,
always-NS about -5800. `traffic-drl train --agent dqn --env toy` with the
`dqn.yaml` settings ends near -1400 per training episode.

Observations worth carrying into Week 6:
- Under-training looks like a bad policy: at 40 episodes the greedy DQN scored
  about -3500 (worse than random) while its noisy training reward looked fine.
- Learning rate 3e-3 was unstable (one of three seeds collapsed to about -6300);
  1e-3 was reliable across three seeds. `dqn.yaml` uses 1e-3.

## Follow-up: first real-SUMO run (Windows) and what it changed

- 36 tests, smoke test, both `env-check`s and 3-episode Q-table/DQN runs all
  passed on real SUMO 1.27.1. This closes the "no real-SUMO run" blocker.
- Finding: the base demand (300 veh/h/approach) is too light to learn from
  (Q-table visited only 7 states, queues of 0-2). Rush hour (900) is the
  meaningful scenario, but it could not be selected.
- [x] `--scenario` for `train` and `env-check` (`TraciEnv(scenario=...)`,
  `load_scenario` in `config.py`): the scenario's route file replaces the
  default demand via SUMO's `--route-files`.
- [x] Per-simulated-second metrics (`TraciEnv.metrics()`): mean queue, average
  wait per vehicle, throughput/hour; counted every second including yellow,
  logged per episode in the training CSV, printed by `env-check`. The training
  reward is counted per agent decision, so the fixed-time comparison must use
  these metrics, not the reward.

## Planned for next week (Week 6)

- [ ] Reward-curve tracking across seeds, hyperparameter sweeps (lr, target
  sync, epsilon decay, gamma), checkpointing (best-so-far and `dqn_final`).
- [ ] Decide the final checkpoint name/format: `DELIVERABLES.md` says
  `checkpoints/dqn_final.pt`, but the file is a numpy archive (no torch), so
  either keep the name or rename to `.npz` across docs and `.gitignore`.
- [ ] First real training run on `TraciEnv` with `configs/dqn.yaml`.

## Blockers / risks

- **Still no real-SUMO run** of any Week 3-5 code. The toy model shows the
  learning code works; it does not show the DQN learns on the real intersection.
- Toy success does not transfer automatically: the real state is 11-dim with
  waiting time, and SUMO episodes are far slower than the toy's.
- DQN has only been compared against the Q-table and naive policies on the
  toy model; the fixed-time baseline comes in Week 8.

## Commits this period

- see `git log` on `main` (Week 5 commits)
