Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| grid_d800_r4 | fixed | 254.6 +- 0.9 | +236.1% | <0.001 | <0.001 | +34.00 | 19.5 | 2150 | 41 | worse |
| grid_d800_r4 | rule | 75.8 +- 1.1 |  |  |  |  | 8.9 | 2862 | 61 | reference |
| grid_d800_r4 | dqh_r4_s0 | 74.2 +- 1.3 | -2.0% | 0.078 | 0.002 | -0.25 | 8.7 | 2868 | 57 | tie |
| grid_d800_r4 | dqh_r4_s1 | 68.4 +- 1.4 | -9.7% | <0.001 | <0.001 | -1.15 | 9.2 | 2896 | 51 | better |
| grid_d800_r4 | dqh_r4_s2 | 71.7 +- 1.2 | -5.3% | <0.001 | <0.001 | -0.69 | 9.3 | 2878 | 58 | better |
| grid_d800_r4 | dqh_r4_s3 | 80.4 +- 1.2 | +6.1% | <0.001 | <0.001 | +0.77 | 8.7 | 2843 | 58 | worse |
