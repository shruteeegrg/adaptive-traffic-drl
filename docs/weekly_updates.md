# Weekly updates after Week 5

Same layout as `logs/TEMPLATE.md`. Week 6 covers 30 Sep to 11 Oct (training, bug-hunting, first demo). Week 7 covers 12 Oct to 29 Oct
(fair benchmark, stronger baseline, stable training, realistic traffic, final results, release). The detailed technical record, with every number,
is in `logs/week-06.md`.

---

# Week 6 Log: Training, convergence debugging, scenarios, first demo

**Date submitted:** 2026-10-11
**Branch / PR:** pushed directly to `main`

## Accomplished last week (Week 5)

- Tabular Q-learning baseline, config-driven state and reward design, a hand-written neural network (backpropagation and Adam, checked against a
  numerical gradient test), and the DQN agent with replay buffer, target network and Huber loss, all in NumPy with no RL libraries.
- First runs on real SUMO (Windows) passed: scenarios change the demand, per-second metrics (queue, wait per vehicle, throughput) work.

## This week (Week 6)

- [x] **Training loop made reliable:** fixed-length 30-minute episodes, a new SUMO seed per episode, evaluation on unseen seeds every few episodes,
  best-checkpoint saving, a `sweep` command for hyperparameter and seed grids (and resuming an interrupted sweep).
- [x] **Better metrics:** counted vehicles held outside a full road (backlog), ranked everything by mean total waiting (queue plus backlog),
  and added phase-switch counts and north-south green fraction.
- [x] **Found and fixed a reward exploit:** the first agent learned to flip the light on every decision. Cause: cost was charged per decision, so a
  long switching decision looked cheap. Fix: charge cost per simulated second, including yellow and backlog; added a regression test and verified
  on SUMO.
- [x] **New scenarios:** tidal traffic (heavy north-south then heavy east-west, flipping every 15 minutes) next to rush hour and low traffic.
- [x] **Rush-hour fix:** raising the discount factor gamma from 0.95 to 0.99 cut waiting from about 200 to about 140 and made seeds consistent.
- [x] **Mixed-scenario training** (one model across scenarios) and per-scenario checkpoint selection; shipped `dqn_final`, `dqn_rush`, `dqn_mixed` as
  NumPy archives.
- [x] **Visualisation module:** training curves and comparison plots, a text table view and a `plot` command.
- [x] **Demo app v1 (Streamlit):** a drawn junction with queued vehicles and signal lamps, fixed timer and DQN side by side on the same traffic,
  a shared waiting chart, honest one-sentence verdicts and a test-results tab.
- [x] Tests grew to cover the exploit fix, the sweep, the demo app (driven headlessly) and DQN convergence across several seeds.

## Results (10 unseen-seed episodes per scenario)

- Tidal: DQN about 91% fewer vehicles waiting than the fixed timer (about 10 against 115) and more vehicles served per hour.
- Rush hour: a tie with the fixed timer (about 140 each).
- Low traffic: both near zero, but the DQN switches the lights far more often than it needs to.
- One model for all patterns (the mixed model) is still weak on rush hour.

## Planned for next week (Week 7)

- Replace "10 episodes, one comparison" with a fair benchmark: 100 fresh-seed episodes, confidence intervals and significance tests.
- Add a stronger baseline than the fixed timer: a density-responsive rule like Nepal's first AI-enabled lights (Lalitpur, 2024).
- Make DQN training stable, add realistic Kathmandu-style traffic, and write up the project (slides, reflective report, diagrams).

## Blockers / risks

- The DQN only wins clearly on uneven traffic; whether it beats a smart non-learning controller is untested.
- Training is sensitive to the random seed and the machine.

---

# Week 7 Log: Fair benchmark, density rule, stable training, realistic traffic, v1.0

**Date submitted:** 2026-10-29
**Branch / PR:** pushed directly to `main`; tagged `v1.0`

## Accomplished last week (Week 6)

- Reliable training and sweeps, reward exploit fixed, tidal scenario, per-scenario checkpoints, visualisation module and demo app v1.
- Result at that point: DQN beat the fixed timer on tidal traffic and tied on rush hour.

## This week (Week 7)

**Write-up and design**
- [x] Demo-day cheat sheet, slide-by-slide explanation and a six-slide deck; a reflective report with 10 draw.io design diagrams (activity, business
  context, class, data flow, ER, functional architecture, sequence, system architecture, use case, workflow).
- [x] A completeness assessment against the contextual report (objectives, requirements, test strategy) listing the gaps, and a day-by-day plan to close them.

**A fair benchmark**
- [x] `traffic-drl compare`: every controller runs on identical seeds; reports mean with 95% confidence interval, Welch and paired t-tests, Cohen's d,
  and a verdict that needs statistical and practical significance (p < 0.05, at least 5% and 2 vehicles). Statistics written without SciPy and
  checked against numerical integration.
- [x] **Density-responsive rule** (Lalitpur-style: count vehicles on each road, give green to the busier one). My first version counted only halted
  vehicles and lost to the fixed timer; I diagnosed it and rewrote it to count all vehicles, as a detector would. Tuned on selection seeds
  (min 10 s, max 40 s, ratio 4, gap 0).
- [x] Regime map: the rule beats the fixed timer in all 16 demand-by-unevenness cells, by 20 to 98%.

**Making the DQN trustworthy**
- [x] Diagnosed unstable training (good early, then drifting) and added: detector-style vehicle counts in the state, Double DQN, soft target updates,
  gradient clipping, learning-rate decay, and **learning from demonstrations** (a frozen buffer of the rule's behaviour that is never overwritten,
  plus a margin loss that stops the network drifting away from it). The last one fixed the instability.

**Realistic Kathmandu-style traffic**
- [x] Route generator for a mixed fleet (62% motorcycles, 22% cars, 8% buses, 8% light goods) with left and right turns; four new scenarios.
- [x] Calibration finding: turning vehicles halve a single lane's capacity (about 1,800 vehicles per hour in total), so my first demand levels
  (900 and 1,100 per road) overloaded the junction and no controller could help. Recalibrated to the measured capacity and kept the calibration curve as evidence.
- [x] A single model trained on 12 randomised demand patterns (the generalist); tested on three held-out scenarios.

**Results and release**
- [x] Consolidated every 100-episode comparison into one table and one figure (`docs/results_final.md`, 44 trained agents, all reported).
- [x] Demo app now shows three controllers (fixed, density rule, DQN) on 9 scenarios, with the final agents shipped in `models/`.
- [x] Clean-install checks on Windows and Mac found three real problems, now fixed: a wrong controller name in the demo, an unused `torch` dependency,
  and SUMO missing from the install (added a `[sumo]` extra). Live demo verified on Windows and on Mac (identical numbers on the same seed).
- [x] Tagged `v1.0`.

## Results (100 fresh-seed episodes per scenario; reference is the tuned density rule)

- Density rule against fixed timer: 20 to 98% less waiting in all 16 cells.
- DQN trained from demonstrations: matches the rule everywhere; on heavy, uneven or near-capacity traffic some agents are 5 to 14% better
  (for example 2 of 4 agents at 4:1 and 1 of 4 at 8:1 are significantly better), but other agents tie or are a few percent worse: the
  benefit is real but not reliable across training runs.
- Generalist: does not yet match the rule on unseen demand (light traffic is its weakest case). Negative result; specialists are kept.

## Planned for next week

- Give the demo (Windows and Mac backups tested) and update the slides to the final results.
- Critical synthesis for the literature review (the supervisor's feedback) and the final report using these results.

## Blockers / risks

- Vehicle-mix shares (MOPIT 2023) are assumptions until checked against the source; Hester et al. 2018 (DQfD) and van Hasselt 2016 (Double DQN)
  references still need verifying before citing.
- Single junction, one lane per road, two phases, motorcycles queue in single file; the rule was tuned on cars-only traffic.
- Survey figures in the contextual report need reconciling when the final report is written.
