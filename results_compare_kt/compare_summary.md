Metric: mean_total_waiting (lower is better). 20 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| rush_hour_kt | fixed | 432.7 +- 4.4 |  |  |  |  | 65.8 | 1823 | 41 | reference |
| rush_hour_kt | fixed30 | 452.2 +- 4.5 | +4.5% | <0.001 | <0.001 | +2.06 | 65.3 | 1740 | 54 | small |
| rush_hour_kt | rule | 432.7 +- 4.4 | +0.0% | 1.000 | 1.000 | +0.00 | 65.8 | 1823 | 41 | tie |
| low_traffic_kt | fixed | 2.3 +- 0.0 |  |  |  |  | 16.1 | 475 | 41 | reference |
| low_traffic_kt | fixed30 | 1.3 +- 0.0 | -45.4% | <0.001 | <0.001 | -34.99 | 8.7 | 479 | 54 | small |
| low_traffic_kt | rule | 0.6 +- 0.0 | -74.4% | <0.001 | <0.001 | -49.74 | 3.7 | 479 | 51 | small |
| tidal_kt | fixed | 294.2 +- 4.2 |  |  |  |  | 55.5 | 1672 | 41 | reference |
| tidal_kt | fixed30 | 306.5 +- 3.4 | +4.2% | <0.001 | <0.001 | +1.51 | 54.9 | 1614 | 54 | small |
| tidal_kt | rule | 234.3 +- 5.3 | -20.4% | <0.001 | <0.001 | -5.89 | 49.9 | 1835 | 49 | better |
| kathmandu_peak | fixed | 631.1 +- 4.6 |  |  |  |  | 65.8 | 1829 | 41 | reference |
| kathmandu_peak | fixed30 | 652.7 +- 6.2 | +3.4% | <0.001 | <0.001 | +1.85 | 66.1 | 1736 | 54 | small |
| kathmandu_peak | rule | 631.1 +- 4.6 | +0.0% | 1.000 | 1.000 | +0.00 | 65.8 | 1829 | 41 | tie |
