Metric: mean_total_waiting (lower is better). 100 episodes per cell, fresh seeds from 30000, the same traffic for every controller. Reference: rule. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal | fixed | 114.0 +- 0.8 | +1482.0% | <0.001 | <0.001 | +35.95 | 20.6 | 2445 | 41 | worse |
| tidal | rule | 7.2 +- 0.1 |  |  |  |  | 7.4 | 2751 | 61 | reference |
| tidal | gen_s0 | 5.9 +- 0.1 | -18.0% | <0.001 | <0.001 | -2.47 | 6.2 | 2756 | 72 | small |
| tidal | gen_s1 | 7.4 +- 0.2 | +2.2% | 0.181 | 0.137 | +0.19 | 7.0 | 2755 | 70 | tie |
| tidal | gen_s2 | 8.6 +- 0.3 | +18.9% | <0.001 | <0.001 | +1.29 | 7.0 | 2749 | 70 | small |
| tidal | gen_s3 | 5.9 +- 0.1 | -18.6% | <0.001 | <0.001 | -2.61 | 6.1 | 2757 | 73 | small |
| rush_hour | fixed | 138.3 +- 1.1 | +9.3% | <0.001 | <0.001 | +2.04 | 22.5 | 3025 | 41 | worse |
| rush_hour | rule | 126.6 +- 1.2 |  |  |  |  | 21.1 | 3064 | 46 | reference |
| rush_hour | gen_s0 | 145.1 +- 1.2 | +14.7% | <0.001 | <0.001 | +3.07 | 18.6 | 2971 | 73 | worse |
| rush_hour | gen_s1 | 143.6 +- 1.1 | +13.5% | <0.001 | <0.001 | +3.03 | 18.6 | 2981 | 72 | worse |
| rush_hour | gen_s2 | 128.3 +- 1.2 | +1.4% | 0.034 | <0.001 | +0.30 | 19.1 | 3046 | 60 | small |
| rush_hour | gen_s3 | 133.4 +- 1.0 | +5.4% | <0.001 | <0.001 | +1.25 | 18.6 | 3023 | 66 | worse |
| low_traffic | fixed | 1.5 +- 0.0 | +590.6% | <0.001 | <0.001 | +73.15 | 11.0 | 475 | 41 | small |
| low_traffic | rule | 0.2 +- 0.0 |  |  |  |  | 1.6 | 480 | 60 | reference |
| low_traffic | gen_s0 | 1.2 +- 0.0 | +441.4% | <0.001 | <0.001 | +95.64 | 8.6 | 475 | 59 | small |
| low_traffic | gen_s1 | 0.9 +- 0.0 | +310.2% | <0.001 | <0.001 | +50.75 | 6.6 | 476 | 60 | small |
| low_traffic | gen_s2 | 1.2 +- 0.0 | +446.9% | <0.001 | <0.001 | +65.95 | 8.8 | 477 | 60 | small |
| low_traffic | gen_s3 | 1.2 +- 0.0 | +460.8% | <0.001 | <0.001 | +45.56 | 9.0 | 475 | 49 | small |
