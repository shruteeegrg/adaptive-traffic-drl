Metric: mean_total_waiting (lower is better). 10 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| diag_fleet_only_900 | fixed | 86.7 +- 5.4 |  |  |  |  | 26.1 | 3232 | 41 | reference |
| diag_fleet_only_900 | rule | 78.4 +- 4.8 | -9.6% | 0.019 | <0.001 | -1.15 | 23.4 | 3251 | 49 | better |
| diag_turns_only_900 | fixed | 481.4 +- 0.1 |  |  |  |  | 57.1 | 1650 | 41 | reference |
| diag_turns_only_900 | rule | 481.4 +- 0.1 | +0.0% | 1.000 | 1.000 | +0.00 | 57.1 | 1650 | 41 | tie |
| kt_load_300 | fixed | 5.0 +- 0.0 |  |  |  |  | 14.2 | 1188 | 41 | reference |
| kt_load_300 | rule | 3.4 +- 0.1 | -32.1% | <0.001 | <0.001 | -13.26 | 9.5 | 1186 | 62 | small |
| kt_load_400 | fixed | 11.5 +- 1.5 |  |  |  |  | 24.3 | 1558 | 41 | reference |
| kt_load_400 | rule | 8.3 +- 1.1 | -27.7% | 0.001 | 0.002 | -1.74 | 17.7 | 1565 | 47 | better |
| kt_load_500 | fixed | 66.6 +- 8.4 |  |  |  |  | 46.5 | 1708 | 41 | reference |
| kt_load_500 | rule | 65.6 +- 7.7 | -1.4% | 0.855 | 0.805 | -0.08 | 45.8 | 1713 | 42 | tie |
| kt_load_600 | fixed | 148.8 +- 7.0 |  |  |  |  | 62.4 | 1782 | 41 | reference |
| kt_load_600 | rule | 143.3 +- 6.6 | -3.7% | 0.212 | 0.053 | -0.58 | 60.0 | 1800 | 42 | tie |
