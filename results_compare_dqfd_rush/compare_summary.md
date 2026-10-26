Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| rush_hour | fixed | 138.3 +- 1.1 | +9.3% | <0.001 | <0.001 | +2.04 | 22.5 | 3025 | 41 | worse |
| rush_hour | fixed30 | 134.8 +- 0.9 | +6.5% | <0.001 | <0.001 | +1.59 | 20.7 | 3029 | 54 | worse |
| rush_hour | rule | 126.6 +- 1.2 |  |  |  |  | 21.1 | 3064 | 46 | reference |
| rush_hour | dqfd_rush_s0 | 126.6 +- 1.1 | +0.1% | 0.932 | 0.888 | +0.01 | 20.1 | 3061 | 52 | tie |
| rush_hour | dqfd_rush_s1 | 123.0 +- 1.0 | -2.8% | <0.001 | <0.001 | -0.65 | 20.1 | 3074 | 51 | small |
| rush_hour | dqfd_rush_s2 | 122.2 +- 1.1 | -3.4% | <0.001 | <0.001 | -0.76 | 20.2 | 3078 | 50 | small |
| rush_hour | dqfd_rush_s3 | 123.6 +- 1.0 | -2.4% | <0.001 | <0.001 | -0.56 | 19.6 | 3070 | 57 | small |
