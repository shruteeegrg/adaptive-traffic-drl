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

## Follow-up 2: the sweep exposed a reward exploit (and the fix)

- Windows sweep (8 settings x 2 seeds x 40 episodes, ~30 min): all 16 runs ended
  with ~450 switches per 1800 s episode (every decision flipped phase: 450 x 4 s
  = 1800 s), ns_green_fraction ~0.5, throughput ~1780/h vs the fixed-time
  baseline's 3037/h, mean_total_waiting ~421 vs 137. Hyperparameters made no
  real difference -- every setting found the same degenerate policy, so that
  ranking is not meaningful.
- Cause: reward was charged once per agent decision. A phase switch burns 3 s of
  yellow inside one decision, so flipping made 3 of every 4 seconds of congestion
  uncharged. (The same flaw had been flagged as a risk in the Week 6 plan.)
- Fix: (1) reward is accrued every simulated second including yellow
  (`features.accrue_cost`); (2) the cost includes the insertion backlog
  (`backlog_weight`); (3) `decision_interval: 5` s (a minimum green) in `dqn.yaml`;
  (4) per-decision switch penalty kept at a small 5 cost units.
  Regression test: a flip-every-4-s policy and a hold policy over the same
  simulated time now cost the same.
- The toy model had the same flaw, so its earlier "convergence" proved less than
  claimed. Re-tuned the toy (balanced demand 0.30/0.25, 400 s episodes; yellow
  charged) and re-checked: with honest accounting, never-switch scores -10275,
  random -13877, a 15 s timer -2079; Q-table -1574 and DQN -1802 beat all three.
- Two things the toy showed that matter for the real runs: the DQN collapses to
  "never switch" unless rewards are scaled small (`reward_scale`, 50 in
  `dqn.yaml`), and the Q-table fails (-9720) without the current phase in its
  state (-1588 with it), so `intersection.yaml` now gives it `[queue, phase]`.
- `traffic-drl baseline` now rounds green seconds to whole decisions
  (`decision_interval`), printing the effective green. Earlier `results_*`
  folders were produced with the old reward and are obsolete for comparison.

## Follow-up 3: reward fix verified on real SUMO; tidal scenario

- Windows, rush hour, 20 DQN episodes (eps still 0.38): switches 55 (was 450),
  mean_total_waiting 224 (ep 10) -> 143 (ep 20) vs fixed-time baseline 139
  (2 episodes, 137-142), throughput 2996 vs 3017/h. The exploit is gone and the
  agent improves with training; it is not yet clearly better than the timer.
  Fixed-time baseline with 5 s decisions: green 40 s, 41 switches, queue 19.5,
  backlog 120, total waiting 139, throughput 3017/h.
- Symmetric rush hour (900/approach) is close to ideal for a 50/50 timer, so a
  tie there is plausible. Added `tidal` (`configs/scenarios/tidal.yaml`,
  `generate_routes.py --tidal 1100 300 --period 900`): heavy axis alternates
  every 15 min (1100 vs 300 veh/h per approach). A 50/50 timer should struggle
  on the heavy axis there; an adaptive controller can follow the demand.

## Follow-up 4: first full sweep after the reward fix (results_sweep_v2)

- 8 settings x 2 seeds x 80 episodes on rush hour, final-policy evaluation on
  unseen seeds vs the fixed-time baseline (total waiting 139, throughput 3017/h,
  41 switches): best DQN runs 177 / 180 / 203 total waiting (throughput 2914 /
  2930 / 2873/h); **no run beat the baseline**, best is ~27% worse.
- Seed dominates hyperparameters: the same setting gives e.g. 177 (seed 0) vs 375
  (seed 1). Bad runs are stuck policies (1-20 switches; ns_green_fraction 0.00 /
  0.12 / 0.85) that starve one direction -- the failure mode moved from
  "always flip" to "never switch". Std over 2 seeds (up to ~170) exceeds the gaps
  between settings, so the ranking is mostly noise.
- The table reports the FINAL policy, but each run also kept a best-so-far
  checkpoint; at 20 episodes the quick run had reached 143, so runs may peak and
  then drift. Not yet evaluated.
- Added: `traffic-drl evaluate` (checkpoint or a folder of `*_best.npz`, ranked,
  same metrics and seeds as `baseline`); per-run `_evals.csv` evaluation
  history in the sweep; optional `backlog` state feature and
  `configs/dqn_backlog.yaml` (12 inputs) as a separate experiment.

## Follow-up 5: best-so-far checkpoints from the sweep (rush hour, 3 episodes, seeds 10000+)

- Baseline: total waiting 139 (episodes 142 / 137), throughput 3017/h, 41 switches.
- Best-so-far checkpoints are much better than the sweep's final policies:
  top four 134.3 / 140.3 / 140.3 / 144.2 total waiting; best throughput 3046/h
  (lr 5e-4, target sync 400, decay 0.93, seed 1 -- whose FINAL policy scored 207, so it
  peaked and drifted). 7 of 16 within ~6% of the baseline or better.
  Several runs never learned (e.g. 425 with 1 switch: stuck policy).
- Reading: on symmetric rush hour the DQN roughly ties the fixed timer. The 134
  is not yet a win: 3 episodes, baseline episodes differ by ~4%, and it is the best of
  16 candidates (selection bias). Needs confirmation on fresh seeds with more
  episodes (`--seed-base`).
- Added `--seed-base` to `evaluate` / `baseline`, and `configs/dqn_tidal.yaml`
  (lr 5e-4, 2 target-sync x 2 decay settings, 4 seeds) for a focused sweep on `tidal`.

## Follow-up 6: plotting module and result files

- `traffic_drl/viz`: `plot_training` (training curves + optional evaluation
  history), `plot_comparison` (controllers side by side per scenario, bars =
  mean over episodes, whiskers = std, dots = episodes) and `comparison_table`
  (the same numbers as text). Baseline is always neutral gray; learned
  controllers take blue, then orange (palette validated: CVD / normal-vision
  separation pass). Drawn by one implementation for the CLI and, later, the app.
- CLI: `traffic-drl plot training --log ... [--evals ...] --out fig.png`,
  `traffic-drl plot compare --item SCENARIO:LABEL=results.csv ... --out fig.png`;
  `evaluate` / `baseline` gain `--save-csv` (per-episode metrics).
- First look at a real training log (one sweep run on rush hour): total waiting
  falls ~275 -> ~160 by episode 40, then drifts back up to ~230 while switches settle
  at ~20 -- the drift the best-checkpoint selection is guarding against.
- Shipped checkpoint renamed `dqn_final.npz` (NumPy archive, not a torch file) in
  the docs and `.gitignore`.
- Commit messages no longer carry week numbers (history reworded; file contents unchanged).

## Follow-up 7: tidal-trained final checkpoint, confirmed on fresh seeds (10 episodes, seeds 30000+)

| scenario | fixed-time: total waiting / throughput | DQN (tidal-trained) | verdict |
|---|---|---|---|
| tidal | 115.0 / 2445 per h | 9.9 / 2749 per h | DQN better in 10/10 episodes (~91% less waiting) |
| rush hour | 139.7 / 3023 | 198.5 / 2747 (99 switches) | fixed-time better (DQN +42% waiting) |
| low traffic | 1.5 / 475 | 24.8 / 389 (avg wait 131 s vs 11 s, 5 switches) | fixed-time better; DQN often parks on one phase |

- Checkpoint rule fixed in advance: most reliable setting (lr 5e-4, target sync 100,
  decay 0.93; 4/4 seeds good), top-ranked seed (1). Saved as `checkpoints/dqn_final.npz`.
- Reading: the DQN is a specialist. Strong on uneven, shifting demand (what it trained on);
  worse than the fixed timer on balanced rush hour and light traffic. Rush-hour-trained
  checkpoints had tied the timer on rush hour, so the training scenario shapes behaviour.
- Hypothesis for the light-traffic failure (untested): the 5-unit switch penalty outweighs
  the cost of one waiting car, and light traffic was never seen in training.
- Built mixed-scenario training: `scenarios:` list in a config (or `--scenario a,b,c`),
  training episodes cycle through them; evaluation scores every scenario and aggregates with
  exp(mean(log1p(waiting))) - 1 so relative changes count equally in light and heavy
  traffic; per-scenario results are kept. The sweep grid accepts `reward.<name>` keys
  (restored after each run) so the switch penalty can be tested. `configs/dqn_mixed.yaml`:
  low / rush / tidal, 2 epsilon decays x switch penalty {0, 5} x 3 seeds, 120 episodes.

## Follow-up 8: demo app

- `traffic-drl demo` launches a Streamlit app (`traffic_drl/app.py`): a live tab that runs the
  fixed timer and the DQN agent side by side on the same traffic (signal state, per-road
  queues, counters, shared "vehicles waiting" chart, one-sentence verdict), a test-results
  tab (saved comparison figure + table; works without SUMO) and a plain-language "how it works" tab.
- `traffic-drl run` streams one controller's episode as JSON lines (the app starts one
  process per controller and polls the files); `TraciEnv.snapshot()` exposes the live state.
- Tested end to end with a fake simulator (real subprocesses) and rendered headlessly in Chrome;
  the real-SUMO live run still needs checking on the Windows machine.

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
