Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| grid_d800_r2 | fixed | 155.4 +- 0.8 | +222.6% | <0.001 | <0.001 | +23.76 | 18.7 | 2559 | 41 | worse |
| grid_d800_r2 | rule | 48.2 +- 1.0 |  |  |  |  | 14.1 | 2983 | 54 | reference |
| grid_d800_r2 | dqh_r2_s0 | 48.6 +- 1.1 | +0.8% | 0.607 | 0.436 | +0.07 | 13.6 | 2981 | 52 | tie |
| grid_d800_r2 | dqh_r2_s1 | 50.7 +- 1.1 | +5.2% | 0.001 | <0.001 | +0.47 | 13.5 | 2973 | 54 | worse |
| grid_d800_r2 | dqh_r2_s2 | 47.0 +- 1.1 | -2.5% | 0.101 | 0.016 | -0.23 | 14.2 | 2989 | 52 | tie |
| grid_d800_r2 | dqh_r2_s3 | 49.5 +- 1.0 | +2.9% | 0.051 | 0.003 | +0.28 | 13.5 | 2978 | 54 | tie |
