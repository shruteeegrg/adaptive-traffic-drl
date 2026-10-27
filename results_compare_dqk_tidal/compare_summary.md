Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal_kt | fixed | 297.0 +- 1.8 | +25.3% | <0.001 | <0.001 | +5.97 | 55.5 | 1669 | 41 | worse |
| tidal_kt | rule | 237.0 +- 2.2 |  |  |  |  | 50.1 | 1824 | 49 | reference |
| tidal_kt | dqk_tidal_s0 | 241.5 +- 2.0 | +1.9% | 0.003 | <0.001 | +0.42 | 48.0 | 1804 | 55 | small |
| tidal_kt | dqk_tidal_s1 | 234.2 +- 2.2 | -1.2% | 0.070 | 0.022 | -0.26 | 48.0 | 1836 | 52 | tie |
| tidal_kt | dqk_tidal_s2 | 243.5 +- 1.9 | +2.7% | <0.001 | <0.001 | +0.62 | 49.4 | 1804 | 53 | small |
| tidal_kt | dqk_tidal_s3 | 243.5 +- 1.8 | +2.8% | <0.001 | <0.001 | +0.65 | 48.8 | 1801 | 56 | small |
