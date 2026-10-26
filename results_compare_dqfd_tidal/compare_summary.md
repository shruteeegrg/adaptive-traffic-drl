Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal | fixed | 114.0 +- 0.8 | +1482.0% | <0.001 | <0.001 | +35.95 | 20.6 | 2445 | 41 | worse |
| tidal | fixed30 | 113.7 +- 0.5 | +1478.4% | <0.001 | <0.001 | +59.02 | 18.8 | 2443 | 54 | worse |
| tidal | rule | 7.2 +- 0.1 |  |  |  |  | 7.4 | 2751 | 61 | reference |
| tidal | dqfd_tidal_s0 | 7.4 +- 0.2 | +2.9% | 0.044 | 0.024 | +0.29 | 7.4 | 2753 | 59 | small |
| tidal | dqfd_tidal_s1 | 7.0 +- 0.1 | -2.7% | 0.022 | 0.021 | -0.33 | 7.2 | 2755 | 63 | small |
| tidal | dqfd_tidal_s2 | 7.2 +- 0.1 | +0.0% | 0.974 | 0.973 | +0.00 | 7.5 | 2755 | 56 | tie |
| tidal | dqfd_tidal_s3 | 6.9 +- 0.1 | -4.0% | <0.001 | <0.001 | -0.51 | 7.1 | 2755 | 63 | small |
