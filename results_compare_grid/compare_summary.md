Metric: mean_total_waiting (lower is better). 30 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| grid_d200_r1 | fixed | 2.5 +- 0.0 |  |  |  |  | 11.1 | 791 | 41 | reference |
| grid_d200_r1 | rule | 0.3 +- 0.0 | -88.4% | <0.001 | <0.001 | -118.54 | 1.3 | 796 | 100 | better |
| grid_d200_r2 | fixed | 2.5 +- 0.0 |  |  |  |  | 11.2 | 787 | 41 | reference |
| grid_d200_r2 | rule | 0.5 +- 0.0 | -82.0% | <0.001 | <0.001 | -83.94 | 2.0 | 793 | 121 | better |
| grid_d200_r4 | fixed | 2.5 +- 0.0 |  |  |  |  | 11.2 | 783 | 41 | reference |
| grid_d200_r4 | rule | 0.4 +- 0.0 | -82.4% | <0.001 | <0.001 | -70.58 | 2.0 | 794 | 79 | better |
| grid_d200_r8 | fixed | 2.5 +- 0.0 |  |  |  |  | 11.1 | 783 | 41 | reference |
| grid_d200_r8 | rule | 0.2 +- 0.0 | -91.8% | <0.001 | <0.001 | -70.65 | 0.9 | 796 | 40 | better |
| grid_d400_r1 | fixed | 5.3 +- 0.0 |  |  |  |  | 11.8 | 1573 | 41 | reference |
| grid_d400_r1 | rule | 2.2 +- 0.1 | -58.7% | <0.001 | <0.001 | -19.65 | 4.9 | 1581 | 82 | better |
| grid_d400_r2 | fixed | 5.6 +- 0.0 |  |  |  |  | 12.3 | 1568 | 41 | reference |
| grid_d400_r2 | rule | 3.3 +- 0.0 | -40.9% | <0.001 | <0.001 | -31.55 | 7.2 | 1580 | 58 | better |
| grid_d400_r4 | fixed | 6.1 +- 0.0 |  |  |  |  | 13.3 | 1565 | 41 | reference |
| grid_d400_r4 | rule | 2.3 +- 0.0 | -61.6% | <0.001 | <0.001 | -76.54 | 5.2 | 1582 | 60 | better |
| grid_d400_r8 | fixed | 6.9 +- 0.1 |  |  |  |  | 14.4 | 1561 | 41 | reference |
| grid_d400_r8 | rule | 1.7 +- 0.0 | -74.8% | <0.001 | <0.001 | -50.66 | 3.7 | 1587 | 62 | better |
| grid_d600_r1 | fixed | 9.2 +- 0.0 |  |  |  |  | 13.5 | 2358 | 41 | reference |
| grid_d600_r1 | rule | 5.9 +- 0.1 | -35.7% | <0.001 | <0.001 | -21.50 | 8.6 | 2363 | 64 | better |
| grid_d600_r2 | fixed | 23.6 +- 1.2 |  |  |  |  | 18.0 | 2294 | 41 | reference |
| grid_d600_r2 | rule | 5.5 +- 0.0 | -76.9% | <0.001 | <0.001 | -8.02 | 7.9 | 2364 | 60 | better |
| grid_d600_r4 | fixed | 99.4 +- 1.4 |  |  |  |  | 20.1 | 1983 | 41 | reference |
| grid_d600_r4 | rule | 4.0 +- 0.0 | -96.0% | <0.001 | <0.001 | -37.09 | 5.6 | 2361 | 64 | better |
| grid_d600_r8 | fixed | 151.0 +- 2.0 |  |  |  |  | 21.1 | 1769 | 41 | reference |
| grid_d600_r8 | rule | 3.4 +- 0.0 | -97.8% | <0.001 | <0.001 | -38.42 | 4.4 | 2361 | 64 | better |
| grid_d800_r1 | fixed | 43.5 +- 1.9 |  |  |  |  | 21.4 | 3015 | 41 | reference |
| grid_d800_r1 | rule | 34.9 +- 1.4 | -19.7% | <0.001 | <0.001 | -1.90 | 19.5 | 3045 | 46 | better |
| grid_d800_r2 | fixed | 155.5 +- 1.6 |  |  |  |  | 18.7 | 2559 | 41 | reference |
| grid_d800_r2 | rule | 47.8 +- 1.7 | -69.3% | <0.001 | <0.001 | -23.87 | 14.1 | 2983 | 54 | better |
| grid_d800_r4 | fixed | 254.6 +- 1.7 |  |  |  |  | 19.5 | 2150 | 41 | reference |
| grid_d800_r4 | rule | 76.1 +- 2.3 | -70.1% | <0.001 | <0.001 | -32.96 | 8.9 | 2862 | 61 | better |
| grid_d800_r8 | fixed | 321.8 +- 1.8 |  |  |  |  | 20.5 | 1880 | 41 | reference |
| grid_d800_r8 | rule | 119.6 +- 2.1 | -62.8% | <0.001 | <0.001 | -38.88 | 5.9 | 2676 | 64 | better |
