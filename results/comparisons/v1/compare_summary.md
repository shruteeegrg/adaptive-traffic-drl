Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal | fixed | 114.0 +- 0.8 |  |  |  |  | 20.6 | 2445 | 41 | reference |
| tidal | fixed30 | 113.7 +- 0.5 | -0.2% | 0.592 | 0.493 | -0.08 | 18.8 | 2443 | 54 | tie |
| tidal | act | 7.2 +- 0.1 | -93.7% | <0.001 | <0.001 | -35.95 | 7.4 | 2751 | 61 | better |
| tidal | dqn_tidal | 10.1 +- 0.2 | -91.1% | <0.001 | <0.001 | -34.48 | 10.2 | 2749 | 38 | better |
| tidal | dqn_rush | 130.8 +- 1.5 | +14.8% | <0.001 | <0.001 | +2.73 | 20.1 | 2504 | 51 | worse |
| tidal | dqn_mixed | 60.4 +- 2.8 | -47.0% | <0.001 | <0.001 | -5.07 | 17.0 | 2476 | 84 | better |
| rush_hour | fixed | 138.3 +- 1.1 |  |  |  |  | 22.5 | 3025 | 41 | reference |
| rush_hour | fixed30 | 134.8 +- 0.9 | -2.5% | <0.001 | <0.001 | -0.69 | 20.7 | 3029 | 54 | small |
| rush_hour | act | 126.6 +- 1.2 | -8.5% | <0.001 | <0.001 | -2.04 | 21.1 | 3064 | 46 | better |
| rush_hour | dqn_tidal | 201.2 +- 1.6 | +45.5% | <0.001 | <0.001 | +8.95 | 19.9 | 2742 | 100 | worse |
| rush_hour | dqn_rush | 139.8 +- 0.9 | +1.1% | 0.039 | 0.004 | +0.29 | 21.1 | 3022 | 52 | small |
| rush_hour | dqn_mixed | 216.0 +- 2.6 | +56.2% | <0.001 | <0.001 | +7.70 | 23.4 | 2698 | 50 | worse |
| low_traffic | fixed | 1.5 +- 0.0 |  |  |  |  | 11.0 | 475 | 41 | reference |
| low_traffic | fixed30 | 1.2 +- 0.0 | -21.9% | <0.001 | <0.001 | -17.95 | 8.6 | 479 | 54 | small |
| low_traffic | act | 0.2 +- 0.0 | -85.5% | <0.001 | <0.001 | -73.15 | 1.6 | 480 | 60 | small |
| low_traffic | dqn_tidal | 18.6 +- 3.1 | +1147.7% | <0.001 | <0.001 | +1.56 | 108.5 | 409 | 5 | worse |
| low_traffic | dqn_rush | 53.8 +- 0.0 | +3507.1% | <0.001 | <0.001 | +3006.53 | 236.5 | 264 | 1 | worse |
| low_traffic | dqn_mixed | 0.5 +- 0.0 | -68.0% | <0.001 | <0.001 | -62.61 | 3.5 | 479 | 121 | small |
