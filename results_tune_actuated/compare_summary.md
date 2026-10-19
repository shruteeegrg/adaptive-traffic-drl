Metric: mean_total_waiting (vehicles waiting, lower is better). 20 episodes per cell, fresh seeds from 20000, the same traffic for every controller. Reference: fixed. Verdict needs p < 0.05 (Welch) and a change of at least 5% and 2 vehicles.

| Scenario | Controller | Waiting (mean +- 95% CI) | Change vs ref | p (Welch) | p (paired) | Cohen d | Wait/vehicle (s) | Veh/hour | Switches | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| tidal | fixed | 115.2 +- 1.7 |  |  |  |  | 20.7 | 2443 | 41 | reference |
| tidal | a_min10_max40_r1.5_g1 | 151.9 +- 2.6 | +31.9% | <0.001 | <0.001 | +7.89 | 19.8 | 2175 | 129 | worse |
| tidal | a_min10_max40_r2.5_g1 | 129.2 +- 2.1 | +12.1% | <0.001 | <0.001 | +3.41 | 16.8 | 2327 | 117 | worse |
| tidal | a_min10_max60_r1.5_g1 | 151.9 +- 2.6 | +31.9% | <0.001 | <0.001 | +7.89 | 19.8 | 2175 | 129 | worse |
| tidal | a_min10_max60_r2.5_g1 | 129.2 +- 2.1 | +12.1% | <0.001 | <0.001 | +3.41 | 16.8 | 2327 | 117 | worse |
| tidal | a_min15_max40_r1.5_g1 | 147.5 +- 0.6 | +28.1% | <0.001 | <0.001 | +12.22 | 17.4 | 2362 | 100 | worse |
| tidal | a_min15_max40_r2.5_g1 | 147.5 +- 0.6 | +28.1% | <0.001 | <0.001 | +12.22 | 17.4 | 2362 | 100 | worse |
| tidal | a_min15_max60_r1.5_g1 | 147.5 +- 0.6 | +28.1% | <0.001 | <0.001 | +12.22 | 17.4 | 2362 | 100 | worse |
| tidal | a_min15_max60_r2.5_g1 | 147.5 +- 0.6 | +28.1% | <0.001 | <0.001 | +12.22 | 17.4 | 2362 | 100 | worse |
| rush_hour | fixed | 139.2 +- 3.3 |  |  |  |  | 22.5 | 3023 | 41 | reference |
| rush_hour | a_min10_max40_r1.5_g1 | 321.3 +- 1.0 | +130.8% | <0.001 | <0.001 | +35.41 | 27.3 | 2249 | 138 | worse |
| rush_hour | a_min10_max40_r2.5_g1 | 251.7 +- 5.5 | +80.8% | <0.001 | <0.001 | +11.63 | 22.3 | 2548 | 116 | worse |
| rush_hour | a_min10_max60_r1.5_g1 | 321.3 +- 1.0 | +130.8% | <0.001 | <0.001 | +35.41 | 27.3 | 2249 | 138 | worse |
| rush_hour | a_min10_max60_r2.5_g1 | 251.7 +- 5.5 | +80.8% | <0.001 | <0.001 | +11.63 | 22.3 | 2548 | 116 | worse |
| rush_hour | a_min15_max40_r1.5_g1 | 199.3 +- 0.8 | +43.1% | <0.001 | <0.001 | +11.84 | 19.4 | 2752 | 100 | worse |
| rush_hour | a_min15_max40_r2.5_g1 | 199.3 +- 0.8 | +43.1% | <0.001 | <0.001 | +11.84 | 19.4 | 2752 | 100 | worse |
| rush_hour | a_min15_max60_r1.5_g1 | 199.3 +- 0.8 | +43.1% | <0.001 | <0.001 | +11.84 | 19.4 | 2752 | 100 | worse |
| rush_hour | a_min15_max60_r2.5_g1 | 199.3 +- 0.8 | +43.1% | <0.001 | <0.001 | +11.84 | 19.4 | 2752 | 100 | worse |
| low_traffic | fixed | 1.5 +- 0.0 |  |  |  |  | 11.0 | 475 | 41 | reference |
| low_traffic | a_min10_max40_r1.5_g1 | 0.4 +- 0.0 | -75.2% | <0.001 | <0.001 | -59.17 | 2.8 | 480 | 60 | small |
| low_traffic | a_min10_max40_r2.5_g1 | 0.4 +- 0.0 | -75.2% | <0.001 | <0.001 | -59.17 | 2.8 | 480 | 60 | small |
| low_traffic | a_min10_max60_r1.5_g1 | 0.4 +- 0.0 | -75.2% | <0.001 | <0.001 | -59.17 | 2.8 | 480 | 60 | small |
| low_traffic | a_min10_max60_r2.5_g1 | 0.4 +- 0.0 | -75.2% | <0.001 | <0.001 | -59.17 | 2.8 | 480 | 60 | small |
| low_traffic | a_min15_max40_r1.5_g1 | 0.4 +- 0.0 | -75.0% | <0.001 | <0.001 | -57.62 | 2.8 | 480 | 60 | small |
| low_traffic | a_min15_max40_r2.5_g1 | 0.4 +- 0.0 | -75.0% | <0.001 | <0.001 | -57.62 | 2.8 | 480 | 60 | small |
| low_traffic | a_min15_max60_r1.5_g1 | 0.4 +- 0.0 | -75.0% | <0.001 | <0.001 | -57.62 | 2.8 | 480 | 60 | small |
| low_traffic | a_min15_max60_r2.5_g1 | 0.4 +- 0.0 | -75.0% | <0.001 | <0.001 | -57.62 | 2.8 | 480 | 60 | small |
