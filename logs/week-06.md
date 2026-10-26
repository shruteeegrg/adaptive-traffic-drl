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

## Rush-hour and mixed follow-up sweeps (gamma)

- `results_sweep_rush_a`: gamma 0.99 took rush-hour waiting from 230-300 (gamma 0.95) to 145-187 on every seed; spread across seeds fell from +-46..83 to +-11..14. Switch penalty 5 vs 0 mattered little once gamma was right.
- `results_sweep_rush_b` (backlog weight, exploration decay): no visible effect.
- `results_sweep_rush_c` (250 episodes, decay 0.98): gamma 0.99 did NOT reproduce (153-304); best checkpoints came at episode 20-30, so longer training looks harmful. Two things changed at once, so the cause is untested.
- `results_sweep_mixed_g99`: low traffic and tidal fine, rush hour still 280-370 -- one model for all patterns is unsolved.
- Fresh-seed check (seeds 30000, 10 episodes): fixed-time rush hour 139.7; best rush checkpoint (gamma 0.995, seed 1) 140.8 -- it MATCHES fixed-time, it does not beat it (rule fixed in advance: must be below 139.7). The checkpoint was picked after seeing four fresh-seed results, so treat the match as slightly optimistic. Mixed seed 2: low traffic 0.5 (fixed 1.5, but 121 switches vs 41), tidal 54.8 (fixed 115).
- Demo uses the best checkpoint per scenario: tidal `dqn_final`, rush `dqn_rush`, low traffic `dqn_mixed`.

## Density-responsive baseline: first version was flawed (tuning on selection seeds 20000, 20 episodes)

- `results_tune_actuated` (first real-SUMO run of `compare`; fixed timer reproduces the earlier numbers: tidal 115.2, rush hour 139.2, low traffic 1.49).
- The first density-responsive controller counted only HALTED vehicles. A lane with green has moving vehicles, so its halted count is about 0 and the controller gapped out as soon as `min_green` ended. Symptoms: `max_green` and `ratio` had no effect (identical results across them), 100 to 138 switches per episode against 41, and waiting 12 to 131 percent WORSE than the fixed timer on tidal and rush hour.
- Fix: the controller is attached to the environment and counts all vehicles on each approach (`approach_vehicle_counts`, detector-style); the halted-queue fallback is kept only for unit tests. Tuning to be re-run.
- Low traffic is a genuine win for adaptive control: wait per vehicle 11.0 s (fixed) vs 2.8 s, although vehicles waiting is tiny for both (1.5 vs 0.4), which is why the verdict rule has a per-metric absolute floor and `compare --metric avg_wait_per_vehicle` exists.

## Density-responsive baseline after the fix (second tuning round, selection seeds 20000, 20 episodes; pasted from the run)

- Best single setting for all scenarios: `min_green 10, max_green 40, ratio 4, gap 0`: tidal 7.3, rush hour 127.7, low traffic 0.2 vehicles waiting.
- Best per scenario: tidal 7.2 (ratio 2.5), rush hour 125.2 (max green 90, ratio 4), low traffic 0.21. Best tuned fixed timers: tidal 115.0 (30 s), rush hour 136.2 (30 s), low traffic 0.81 (20 s).
- A tuned detector rule beats the fixed timer on all three scenarios, including rush hour (about 8 to 10 percent), and beats the original DQN everywhere (DQN numbers are from different seeds: tidal 9.9, rush hour 140.8, low traffic 0.5; to be settled by `compare` on 100 fresh episodes).
- Likely cause of the DQN's deficit: it sees only halted vehicles, the rule sees all vehicles on the approach. New state feature `vehicles` and `configs/dqn_v.yaml` remove that gap.

## First definitive comparison (`results_compare_v1`: 100 episodes per cell, fresh seeds from 30000, same traffic for every controller)

Vehicles waiting, mean +- 95% CI (verdict needs p < 0.05, at least 5 percent and 2 vehicles):

| Scenario | Fixed 40 s | Fixed 30 s | Density rule (min 10, max 40, ratio 4) | DQN tidal | DQN rush | DQN mixed |
|---|---|---|---|---|---|---|
| Tidal | 114.0 | 113.7 (tie) | **7.2** (-94%) | 10.1 (-91%) | 130.8 (+15%) | 60.4 (-47%) |
| Rush hour | 138.3 | 134.8 (small) | **126.6** (-8.5%, better) | 201.2 (+46%) | 139.8 (+1%, small) | 216.0 (+56%) |
| Low traffic | 1.5 | 1.2 | 0.2 (wait per vehicle 1.6 s vs 11.0 s) | 18.6 (+1148%) | 53.8 (+3507%, 1 switch) | 0.5 |

- The tuned density rule beats the fixed timer everywhere and beats every DQN checkpoint in every scenario.
- The generalisation test promised in the contextual report (trained on rush hour, tested on low traffic) FAILS: the rush-hour DQN almost never switches (1 switch per episode), so the cross street starves.

## DQN with detector-style input (`dqn_v.yaml`), 120 episodes, 4 seeds, plain vs Double DQN

- Final-policy waiting is worse than the best checkpoints and bounces from one evaluation to the next (tidal seed 0: 7, 58, 44, 43, 52, 56 ...; rush hour seed 2: 343, 171, 160, 161, 210, 235, 389 ...). Several runs were as good as the rule at episode 10 (tidal 7.1) and then degraded.
- Double DQN: no consistent benefit (tidal mean 43 vs 54, rush hour 198 vs 165, both with large spread).
- Diagnosis: the input is no longer the limit, training stability is. Next: soft target update, gradient clipping, learning-rate decay, 5-episode checkpoint selection (`dqn_v_stable.yaml`) and seeding the replay buffer with the density rule's experience (`dqn_v_teacher.yaml`).
- Sweeps now score each run's BEST checkpoint on fresh ranking seeds (20000s), not the last policy.

## Tidal sweeps with the steadier recipe and the teacher (`results_sweep_vs_tidal`, `results_sweep_vt_tidal`; 120 episodes, 4 seeds, 5-episode selection)

- Best checkpoint on fresh ranking seeds, waiting: stable only 10.1 / 26.1 / 37.2 / 32.9; stable + teacher 23.5 / 12.4 / 19.0 / 13.8 (density rule 7.2, old DQN 10.1, fixed 114).
- Soft target update, gradient clipping and learning-rate decay alone did not stop the drift (all four runs degrade after episode 10 to 30). Seeding with the teacher kept two of four seeds at about 12 to 18 for all 120 episodes; the other two still drifted (to 64 and 50). Nothing reached the rule, and ordinary Q-learning did not improve on the teacher.
- Hypothesis: the teacher's transitions are overwritten in the replay buffer after about 55 episodes, after which the network trains only on its own behaviour. Next: `dqn_v_dqfd.yaml` (frozen demonstration buffer, a quarter of each batch from it, large-margin loss).

## Realistic traffic scenarios (Kathmandu-style)
- `scripts/generate_routes.py` gained `--fleet kathmandu` (vehicle-type distribution: 62% motorcycle, 22% car, 8% bus, 8% light goods) and `--turns LEFT RIGHT` (turning movements on the junction's existing connections). Output for the old scenarios is byte-identical.
- New scenarios: `rush_hour_kt` (900/approach), `low_traffic_kt` (120), `tidal_kt` (1100/300, flips every 900 s), `kathmandu_peak` (1100 even, assumed saturation level). All with 15% left and 15% right turners.
- The fleet shares come from the project plan (MOPIT 2023) and are assumptions until verified against the source. Motorcycles still queue single file (no sublane model), so they take less road but do not filter: a stated limitation.
- Not yet checked in real SUMO: whether turning vehicles block the single lane (left turners yield to oncoming traffic on the permissive green) and whether all vehicles complete their trips.
