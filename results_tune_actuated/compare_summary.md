Metric: mean_total_waiting (lower is better). 20 episodes per cell, fresh seeds from 20000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 (units of the metric).

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal | fixed | 115.2 +- 1.7 |  |  |  |  | 20.7 | 2443 | 41 | reference |
| tidal | a_min10_max40_r1.5_g0 | 5.9 +- 0.2 | -94.9% | <0.001 | <0.001 | -43.30 | 6.3 | 2759 | 74 | better |
| tidal | a_min10_max40_r2.5_g0 | 7.2 +- 0.2 | -93.8% | <0.001 | <0.001 | -42.87 | 8.0 | 2755 | 63 | better |
| tidal | a_min10_max60_r1.5_g0 | 6.0 +- 0.2 | -94.8% | <0.001 | <0.001 | -43.29 | 6.4 | 2757 | 74 | better |
| tidal | a_min10_max60_r2.5_g0 | 7.4 +- 0.1 | -93.6% | <0.001 | <0.001 | -42.94 | 8.3 | 2756 | 47 | better |
| tidal | a_min15_max40_r1.5_g0 | 14.0 +- 1.5 | -87.8% | <0.001 | <0.001 | -30.06 | 8.5 | 2721 | 60 | better |
| tidal | a_min15_max40_r2.5_g0 | 12.4 +- 1.0 | -89.2% | <0.001 | <0.001 | -35.55 | 8.7 | 2725 | 59 | better |
| tidal | a_min15_max60_r1.5_g0 | 8.2 +- 0.4 | -92.9% | <0.001 | <0.001 | -41.51 | 7.5 | 2750 | 58 | better |
| tidal | a_min15_max60_r2.5_g0 | 7.3 +- 0.1 | -93.7% | <0.001 | <0.001 | -42.97 | 8.2 | 2755 | 46 | better |
| rush_hour | fixed | 139.2 +- 3.3 |  |  |  |  | 22.5 | 3023 | 41 | reference |
| rush_hour | a_min10_max40_r1.5_g0 | 199.7 +- 1.0 | +43.5% | <0.001 | <0.001 | +11.74 | 19.5 | 2749 | 100 | worse |
| rush_hour | a_min10_max40_r2.5_g0 | 152.2 +- 1.5 | +9.4% | <0.001 | <0.001 | +2.39 | 18.6 | 2944 | 77 | worse |
| rush_hour | a_min10_max60_r1.5_g0 | 199.7 +- 1.0 | +43.5% | <0.001 | <0.001 | +11.74 | 19.5 | 2749 | 100 | worse |
| rush_hour | a_min10_max60_r2.5_g0 | 152.2 +- 1.5 | +9.4% | <0.001 | <0.001 | +2.39 | 18.6 | 2944 | 77 | worse |
| rush_hour | a_min15_max40_r1.5_g0 | 197.9 +- 0.8 | +42.2% | <0.001 | <0.001 | +11.56 | 19.4 | 2751 | 99 | worse |
| rush_hour | a_min15_max40_r2.5_g0 | 152.2 +- 1.5 | +9.4% | <0.001 | <0.001 | +2.39 | 18.6 | 2944 | 77 | worse |
| rush_hour | a_min15_max60_r1.5_g0 | 197.9 +- 0.8 | +42.2% | <0.001 | <0.001 | +11.56 | 19.4 | 2751 | 99 | worse |
| rush_hour | a_min15_max60_r2.5_g0 | 152.2 +- 1.5 | +9.4% | <0.001 | <0.001 | +2.39 | 18.6 | 2944 | 77 | worse |
| low_traffic | fixed | 1.5 +- 0.0 |  |  |  |  | 11.0 | 475 | 41 | reference |
| low_traffic | a_min10_max40_r1.5_g0 | 0.2 +- 0.0 | -84.5% | <0.001 | <0.001 | -60.72 | 1.7 | 479 | 68 | small |
| low_traffic | a_min10_max40_r2.5_g0 | 0.2 +- 0.0 | -85.9% | <0.001 | <0.001 | -65.04 | 1.6 | 480 | 60 | small |
| low_traffic | a_min10_max60_r1.5_g0 | 0.2 +- 0.0 | -84.5% | <0.001 | <0.001 | -60.72 | 1.7 | 479 | 68 | small |
| low_traffic | a_min10_max60_r2.5_g0 | 0.2 +- 0.0 | -85.9% | <0.001 | <0.001 | -65.04 | 1.6 | 480 | 60 | small |
| low_traffic | a_min15_max40_r1.5_g0 | 0.3 +- 0.0 | -80.8% | <0.001 | <0.001 | -43.77 | 2.1 | 479 | 67 | small |
| low_traffic | a_min15_max40_r2.5_g0 | 0.2 +- 0.0 | -85.4% | <0.001 | <0.001 | -64.78 | 1.6 | 480 | 60 | small |
| low_traffic | a_min15_max60_r1.5_g0 | 0.3 +- 0.0 | -80.8% | <0.001 | <0.001 | -43.77 | 2.1 | 479 | 67 | small |
| low_traffic | a_min15_max60_r2.5_g0 | 0.2 +- 0.0 | -85.4% | <0.001 | <0.001 | -64.78 | 1.6 | 480 | 60 | small |
