Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| kathmandu_peak | fixed | 72.8 +- 1.9 | +5.6% | 0.007 | <0.001 | +0.38 | 47.3 | 1695 | 41 | worse |
| kathmandu_peak | rule | 68.9 +- 2.1 |  |  |  |  | 46.5 | 1701 | 42 | reference |
| kathmandu_peak | dqk_peak_s0 | 70.7 +- 1.9 | +2.5% | 0.228 | 0.185 | +0.17 | 46.5 | 1702 | 40 | tie |
| kathmandu_peak | dqk_peak_s1 | 67.2 +- 2.1 | -2.5% | 0.263 | 0.185 | -0.16 | 46.0 | 1711 | 42 | tie |
| kathmandu_peak | dqk_peak_s2 | 72.7 +- 2.1 | +5.5% | 0.013 | 0.003 | +0.36 | 47.2 | 1691 | 41 | worse |
| kathmandu_peak | dqk_peak_s3 | 71.8 +- 1.8 | +4.2% | 0.042 | 0.029 | +0.29 | 47.3 | 1702 | 41 | small |
