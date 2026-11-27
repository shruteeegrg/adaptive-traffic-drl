Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| grid_d800_r8 | fixed | 321.9 +- 1.0 | +170.6% | <0.001 | <0.001 | +39.78 | 20.6 | 1878 | 41 | worse |
| grid_d800_r8 | rule | 119.0 +- 1.0 |  |  |  |  | 5.9 | 2677 | 64 | reference |
| grid_d800_r8 | dqh_r8_s0 | 117.2 +- 1.3 | -1.5% | 0.027 | <0.001 | -0.31 | 5.9 | 2689 | 64 | small |
| grid_d800_r8 | dqh_r8_s1 | 118.8 +- 1.0 | -0.1% | 0.864 | 0.320 | -0.02 | 5.9 | 2678 | 64 | tie |
| grid_d800_r8 | dqh_r8_s2 | 105.6 +- 1.3 | -11.2% | <0.001 | <0.001 | -2.25 | 5.3 | 2737 | 60 | better |
| grid_d800_r8 | dqh_r8_s3 | 119.0 +- 1.1 | +0.0% | 0.951 | 0.790 | +0.01 | 5.9 | 2678 | 64 | tie |
