# Generalist agent v2: results

The earlier generalist (`models/gen_s3.npz`) was trained on 12 cars-only, straight-only patterns with no quiet cases, then
met motorcycle-heavy traffic with turns in the web app. Its weakness was a mismatch between what it learned from and what a
client builds, so v2 is trained on the same space of traffic a client can describe (`traffic_drl/pool.py`).

## Method (reproduce with the scripts named)

- Pools (`scripts/make_client_pool.py`, three different seeds, no scenario or demand pattern shared):
  **train** 30 scenarios, **select** 8, **test** 12 random + the 5 web-app presets. Demand 80 to 1300 veh/h on the heavier
  axis; balanced, uneven and flipping patterns; 30% cars-only, otherwise random mixed fleets; 75% with turning; all 30 minutes.
- Recipe (`scripts/train_generalist.py`): the shipped one (`configs/dqn_v_dqfd.yaml`, learning from the density rule's
  demonstrations with a frozen buffer and margin loss), 60 demonstration episodes, 300 training episodes, 4 seeds x two
  network widths (64 and 128) = 8 runs, about 24 minutes each.
- Checkpoints and the run were chosen on the **select** pool only. The density rule and fixed timer were scored on the
  same select scenarios and seeds.
- Rule: the candidate was fixed (best select score: `h64_s1`) **before** the test pool was used, and the test pool was run once.
  Test seeds start at 30000; 20 episodes per controller per scenario (`scripts/eval_generalist.py`).

## Selection result (select pool, mean vehicles waiting, lower is better; rule 4.77, fixed 8.83)

| Run | Select score | vs rule |
|---|---|---|
| h64_s1 (shipped as `models/gen_v2.npz`) | 4.66 | -2.4% |
| h128_s2 | 4.67 | -2.0% |
| h128_s1 | 4.74 | -0.6% |
| h64_s0 | 4.84 | +1.4% |
| h64_s2 | 5.04 | +5.7% |
| h128_s3 | 5.40 | +13.2% |
| h128_s0 | 5.43 | +13.9% |
| h64_s3 | 5.52 | +15.7% |

## Test result (held-out)

Test pool: 17 scenarios, 20 episodes per controller each, test seeds from 30000. Mean vehicles waiting (lower is better). Verdicts need p < 0.05 and a 5% / 2-vehicle change.

| Scenario | Fixed | Rule | Old generalist | New agent | New vs rule | New vs old |
|---|---|---|---|---|---|---|
| preset_balanced | 41.8 | 34.7 | 26.2 | 9.8 | better | better |
| preset_morning_rush | 157.8 | 84.0 | 110.4 | 70.8 | better | better |
| preset_near_capacity | 364.8 | 366.0 | 388.5 | 341.4 | better | better |
| preset_quiet | 1.8 | 0.5 | 1.0 | 0.5 | tie | small |
| preset_tidal_swing | 184.9 | 117.4 | 146.9 | 96.6 | better | better |
| test_00 | 1.6 | 0.2 | 1.0 | 0.2 | tie | small |
| test_01 | 2.8 | 0.8 | 1.3 | 0.7 | small | small |
| test_02 | 210.8 | 142.8 | 147.7 | 130.9 | better | better |
| test_03 | 716.8 | 715.3 | 777.0 | 724.6 | small | better |
| test_04 | 96.6 | 4.0 | 3.9 | 5.1 | small | small |
| test_05 | 1.2 | 0.1 | 0.6 | 0.1 | small | small |
| test_06 | 94.5 | 89.0 | 83.7 | 51.5 | better | better |
| test_07 | 1.6 | 0.2 | 0.8 | 0.4 | small | small |
| test_08 | 1.1 | 0.1 | 0.5 | 0.0 | small | small |
| test_09 | 5.0 | 2.6 | 2.8 | 2.2 | small | small |
| test_10 | 1.1 | 0.1 | 0.2 | 0.1 | small | small |
| test_11 | 3.2 | 0.5 | 0.9 | 0.5 | small | small |

New agent vs rule: better in 6, tie or small in 11, worse in 0 scenarios.
Old generalist vs rule: better in 2, tie or small in 11, worse in 4.
New agent vs old generalist: better in 7, tie or small in 10, worse in 0.

Geometric mean change in waiting (relative to the rule): fixed +91.5%, old generalist +17.7%, new agent -12.3%.
New agent vs old generalist: -25.5%.

## How to read this

- The new agent is never significantly worse than the density rule on the 17 test scenarios, is better in 6, and is better
  than the old generalist in 7 and worse in none.
- **Seed luck is real.** Only 3 of the 8 trained runs scored within 1% of the rule or better on the select pool; the others
  were up to 16% worse. The shipped agent is the best of 8 chosen on the select pool, and the test pool is independent of
  that choice, but a freshly trained seed should be expected to vary. This is why training jobs train several seeds.
- **The rule was tuned on cars-only traffic.** Several large gaps (for example `preset_balanced`, 34.7 vs 9.8) are in mixed-fleet
  traffic where the rule's settings were not tuned. Part of the agent's advantage may be a mis-tuned rule rather than a
  better policy. Re-tuning the rule on mixed traffic and repeating the comparison is the fair next test.
- Most light-traffic scenarios are ties: every controller keeps vehicles moving, so differences are below the practical floor.
- Single junction, one lane per road, two phases; simulation only.
