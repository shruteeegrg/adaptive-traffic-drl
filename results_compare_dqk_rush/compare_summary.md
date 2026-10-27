Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| rush_hour_kt | fixed | 11.5 +- 0.4 | +30.7% | <0.001 | <0.001 | +1.35 | 24.3 | 1559 | 41 | worse |
| rush_hour_kt | rule | 8.8 +- 0.4 |  |  |  |  | 18.7 | 1564 | 46 | reference |
| rush_hour_kt | dqk_rush_s0 | 7.6 +- 0.3 | -13.7% | <0.001 | <0.001 | -0.73 | 16.2 | 1570 | 48 | small |
| rush_hour_kt | dqk_rush_s1 | 7.8 +- 0.3 | -11.6% | <0.001 | <0.001 | -0.57 | 16.5 | 1569 | 47 | small |
| rush_hour_kt | dqk_rush_s2 | 8.0 +- 0.4 | -8.9% | 0.004 | 0.001 | -0.42 | 17.0 | 1566 | 47 | small |
| rush_hour_kt | dqk_rush_s3 | 7.7 +- 0.3 | -12.9% | <0.001 | <0.001 | -0.65 | 16.3 | 1569 | 47 | small |
