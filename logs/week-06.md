# Week 6 Log — Training, Convergence Debugging, Checkpointing

**Date submitted:** 2026-10-05
**Branch / PR:** pushed directly to `main`

## Accomplished last week (Week 5 + follow-up)

- DQN agent (replay buffer, target network, Huber loss), `train --agent dqn`.
- First real-SUMO runs on Windows (SUMO 1.27.1): 40 tests, smoke test, env-checks
  and short Q-table/DQN runs all passed. Scenarios verified to change demand:
  mean queue 1.0 (low) / 2.6 (default) / 14.5 (rush) under a fixed alternating policy.
- `--scenario` support and per-second metrics (mean queue, avg wait/vehicle, throughput/hour).
- Real-SUMO speed: 3 rush-hour episodes of 600 decisions in 6.6 s (~2 s/episode).
  Near-random agent on rush hour: mean queue ~7.0-7.3, avg wait ~14.4-15.1 s,
  throughput ~1630/h -- stable across episodes, so the metrics are low-noise.

## This week (Week 6)

- [x] Fixed-length episodes: `configs/dqn.yaml` sets `episode_length: 1800` and no
  decision cap. A switching decision costs ~4 simulated seconds and a
  non-switching one 1 s, so a decision-count cap gave frequent-switchers more
  simulated time per episode and made rewards incomparable across policies.
- [x] Per-episode SUMO seeds (`TraciEnv(seed=...)`, `--seed base + reset count`).
  Before this every episode used SUMO's default seed and replayed the same run.
  Evaluation uses seeds >= 10000, never seen in training.
- [x] `evaluate()` (greedy, no learning, unseen seeds) and periodic evaluation
  in `train_agent` (`eval_every`): keeps a best-so-far checkpoint
  (`dqn_best.npz`) chosen by mean queue (reward where no metrics exist).
- [x] `traffic-drl sweep`: grid in the `sweep:` config section x seeds, each run
  trained then evaluated on unseen seeds; writes `sweep_runs.csv`,
  `sweep_summary.csv` (mean/std over seeds, ranked by mean queue), per-run logs
  and best checkpoints under `runs/`.
- [x] `tests/test_sweep.py` (6 tests); full suite 46 tests.

## Follow-up: first 10-episode real-SUMO run changed the metric

- 10 training episodes + 2 evaluations ran in 31.5 s (~2 s/episode, far below the
  ~10 s estimate), so a full sweep is ~30 minutes, not hours.
- Greedy evaluation on unseen seeds (rush hour): episode 5 mean_queue 3.22,
  throughput 1782/h; episode 10 mean_queue 3.29, throughput 1780/h.
- Problem spotted: arrived vehicles imply ~1780/h served against 3600/h offered,
  yet mean_queue is only ~3. Approach edges are 92.8 m (~12 vehicles), so overflow
  waits in SUMO's insertion backlog, which `mean_queue` cannot see. Ranking by
  mean_queue could therefore reward policies that merely hide congestion.
- [x] Added `mean_backlog` (vehicles waiting to be inserted, per simulated second)
  and `mean_total_waiting` = mean_queue + mean_backlog. Best-checkpoint selection
  and sweep ranking now use `mean_total_waiting`.
- [x] `FixedTimeAgent` (42 s greens, matching the network's own plan) and
  `traffic-drl baseline`, evaluated through the same loop and metrics as the
  agents. Pulled forward from Week 8 because no DQN number can be interpreted
  without it.

## Planned for next week (Week 7)

- [ ] Run the sweep on real SUMO (rush hour), pick settings, train and ship the
  final checkpoint (`dqn_final`; name/format still to decide -- it is a numpy
  archive, not a torch file).
- [ ] Visualization module: plots from saved logs (reward, wait time,
  throughput), wired into `traffic-drl evaluate`.

## Blockers / risks

- Sweep and seed behaviour tested with the toy model and a fake `traci` only;
  the real-SUMO check (does `--seed` change runs, how long does a 1800 s
  episode take, does the DQN improve over ~10-40 episodes) is the next Windows run.
- Route flows use `vehsPerHour`, which departs vehicles at regular intervals, so
  demand itself is deterministic; seeds vary driver behaviour only. Poisson
  arrivals (`probability` flows) would add demand variability if results look
  too tidy.
- Episodes end by time limit; the DQN treats that as terminal (no bootstrap),
  a small known bias for a time-limited task.
- Throughput/avg wait are computed from vehicles entering/arriving; a backed-up
  entry edge delays insertions, which can flatter wait under heavy overload.
  Compare controllers on mean queue AND throughput together.

## Commits this period

- see `git log` on `main` (Week 6 commits)
