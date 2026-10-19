# Seven-day coding plan: the strongest project we can build

Focus: code and experiments only. No thesis writing or demo work in these seven days.

**The question the project will answer:** *Does a learned signal controller beat what Nepal actually uses (a density-responsive adaptive rule, as in Lalitpur's 2024 pilot) and a plain fixed timer, on realistic Kathmandu-style traffic, with proper statistics, and where does it help or not?*

**Rules fixed in advance (so results cannot move them):**
- Tune every controller, including the baselines, on selection seeds (20000s). Report only on fresh seeds (30000s).
- A controller counts as "better" only if Welch p < 0.05 **and** the change is at least 5 percent of the reference **and** at least 2 vehicles waiting, on 100 episodes.
- Report distributions across independently trained agents, not only the best checkpoint.
- Negative and tied results are reported as they are.

Legend: **Mac** = what I build and test (fake simulator); **Win** = what you run on the Windows laptop; **Gate** = the decision the day's results force.

## Day 1: fair benchmark and first real numbers
- **Mac (done, pushed):** `traffic-drl compare` (CI, Welch and paired t-tests, effect size, verdict), density-responsive baseline, baseline tuning script, Double DQN option and sweep config, tests.
- **Win (about 3 h, unattended):**
  1. `python scripts/tune_actuated.py ...` (about 30 min)
  2. `traffic-drl compare ... --episodes 100` with fixed, tuned actuated, `dqn_final`, `dqn_rush`, `dqn_mixed` (about 1.5 h)
  3. `traffic-drl sweep --config configs/dqn_ddqn.yaml ...` (about 1 h)
- **Gate:** does the DQN beat the *tuned density rule*, per scenario? If yes, we go on to realism and robustness. If not on a scenario, Days 3 to 4 add a design-improvement step for that scenario (see the contingency table).
- **Have by end of day:** first statistically tested ranking of fixed, actuated and DQN on the three existing scenarios; Double DQN verdict.

## Day 2: realistic traffic
- **Mac:**
  - Route generator: motorcycle-heavy fleet (about 62 percent motorcycles, 22 percent cars, 8 percent buses, 8 percent other, from MOPIT 2023), as a SUMO vehicle-type distribution.
  - Turning vehicles (left and right, for example 15 percent each), using connections the junction already has.
  - New scenarios: `rush_hour_kt`, `low_traffic_kt`, `tidal_kt`, and `kathmandu_peak` (about 1,000 to 1,200 veh/h per approach, calibrated to the corridor figures, assumptions written down).
  - Tests for the generators and scenario configs.
- **Win (about 1 h):** `compare` fixed vs tuned actuated on the new scenarios (the DQN has not been trained for them yet); a quick look in `sumo-gui` to check the traffic looks sensible.
- **Gate:** is the new traffic sensible (queues form, no deadlocks, vehicles complete trips)? If motorcycles behave unrealistically in a single lane, I add the optional sublane model flag and you test it.
- **Have:** a heterogeneous, turning, Kathmandu-calibrated scenario set with baseline numbers.

## Day 3: train for the realistic scenarios
- **Mac:** training stability options (learning-rate decay, gradient clipping), because best checkpoints so far appear early and later episodes drift; sweep configs for the new scenarios using the best Day 1 settings (gamma 0.99; Double DQN if it helped).
- **Win (about 3 h):** sweep on the Kathmandu-style scenarios, 4 seeds each, with and without learning-rate decay.
- **Gate:** does decay remove the late-training drift? Pick the training recipe.
- **Have:** a training recipe backed by data; trained specialists for the realistic scenarios.

## Day 4: one robust model (the stretch goal)
- **Mac:** randomised-demand training: every training episode draws a fresh demand pattern (load, unevenness, flip timing) instead of cycling three fixed scenarios, so a single model faces many patterns. Plus the evaluation harness for it.
- **Win (about 3 h):** train the generalist, 4 seeds.
- **Gate:** is the generalist within 5 percent of the specialists on each scenario? If yes, it replaces the three models. If no, we report it as a negative result and keep specialists.
- **Have:** an answer to "can one model do everything?", in either direction.

## Day 5: the regime map
- **Mac:** regime-map tool: a grid of total demand by unevenness (for example 5 x 4 cells), each cell evaluated for fixed, tuned actuated, best DQN specialist and the generalist; heatmap of percent change and verdicts.
- **Win (about 3 h):** run the grid.
- **Have:** the main scientific figure: where learning helps, where a simple rule is enough, where nothing helps.

## Day 6: final models and the long run
- **Mac:** a "final training" config (500 episodes, best-checkpoint selection every 10 episodes, reward curve logged); evaluation of every trained seed, not only the best; figures of reward and waiting curves.
- **Win (overnight, about 4 h):** final training and the full 100-episode comparison on fresh seeds for every controller on every scenario.
- **Have:** the final result set: means, 95 percent confidence intervals, p-values, effect sizes, verdicts; across-seed spread; the 500-episode training curve.

## Day 7: freeze and verify
- **Mac:** assemble results tables and figures from the saved files; copy the winning checkpoints; add the density-responsive controller and the new scenarios to the demo app's dropdowns; README run instructions; fresh-clone install check.
- **Win:** full test suite, one end-to-end `compare` run from a clean clone, tag `v1.0`.
- **Have:** a reproducible repository and a fixed set of numbers that nothing else will change.

## What we will have by Day 7
1. A **fair benchmark**: fixed timer, tuned density-responsive rule (the Lalitpur-style controller), DQN and Double DQN specialists, and possibly a single generalist, all tested on 100 fresh-seed episodes with confidence intervals, p-values, effect sizes and a practical-significance rule.
2. **Realistic traffic**: a Kathmandu vehicle mix and turning movements, in addition to the original cars-only scenarios, and a peak scenario calibrated to published corridor figures.
3. **Evidence for each design choice**: gamma, Double DQN, learning-rate decay, training length, and how much results vary between independently trained agents.
4. A **regime map** showing when adaptive learning helps.
5. An honest answer on **one model versus one per scenario**.
6. A **reproducible, tagged repository** with the final checkpoints and the commands that regenerate every number.

## Contingencies
| If this happens | Then |
|---|---|
| Tuned density rule beats the DQN on a scenario (Day 1) | Day 3 adds a design step for that scenario: richer state (backlog, arrival trend), a longer-horizon variant, and a hybrid (DQN chooses among the rule's options). Report the rule as the winner if the DQN cannot catch it. |
| DQN beats it on uneven traffic only | That is the central finding. The regime map (Day 5) makes it quantitative. |
| Motorcycles look wrong in a single lane (Day 2) | Try SUMO's sublane model; if it is unstable, use the minimal fleet and state the limitation. |
| Generalist fails (Day 4) | Report it; keep specialists; use the time for a second training recipe. |
| A Windows run stalls or the laptop sleeps | Sweeps and `compare` outputs are saved per run; the sweep can resume. Sleep is already disabled. |
| Something runs long | Reduce episodes per cell (100 to 50) for the regime map only; keep 100 for the final table. |

## Daily rhythm
- I build and test on the Mac, push, and send you one or two commands.
- You run them on Windows (mostly unattended), push the result folders, and paste the summary table.
- Each evening I read the results, apply the day's gate, and adjust the next day.
