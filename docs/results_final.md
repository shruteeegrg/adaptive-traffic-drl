# Final results: learned agents against the tuned density rule

Mean total waiting (vehicles; lower is better), 100 episodes per cell on fresh seeds (30000+), the same traffic for every controller. Change is against the tuned rule. Verdicts use the rule fixed in advance: Welch p < 0.05 and a change of at least 5% and 2 vehicles. Every independently trained agent is reported, not only the best.

| Scenario | Agents trained as | Fixed | Rule | Agents (mean of n) | Range of agents | Mean change vs rule | Agents: better / tie or small / worse |
|---|---|---|---|---|---|---|---|
| tidal | specialist, cars | 114.0 | 7.2 | 7.1 (n=4) | 6.9 to 7.4 | -0.9% | 0 / 4 / 0 |
| rush_hour | specialist, cars | 138.3 | 126.6 | 123.9 (n=4) | 122.2 to 126.6 | -2.1% | 0 / 4 / 0 |
| grid_d800_r2 | specialist, cars | 155.4 | 48.2 | 48.9 (n=4) | 47.0 to 50.7 | +1.6% | 0 / 3 / 1 |
| grid_d800_r4 | specialist, cars | 254.6 | 75.8 | 73.7 (n=4) | 68.4 to 80.4 | -2.7% | 2 / 1 / 1 |
| grid_d800_r8 | specialist, cars | 321.9 | 119.0 | 115.1 (n=4) | 105.6 to 119.0 | -3.2% | 1 / 3 / 0 |
| tidal_kt | specialist, Kathmandu mix | 297.0 | 237.0 | 240.7 (n=4) | 234.2 to 243.5 | +1.5% | 0 / 4 / 0 |
| rush_hour_kt | specialist, Kathmandu mix | 11.5 | 8.8 | 7.8 (n=4) | 7.6 to 8.0 | -11.8% | 0 / 4 / 0 |
| kathmandu_peak | specialist, Kathmandu mix | 72.8 | 68.9 | 70.6 (n=4) | 67.2 to 72.7 | +2.4% | 0 / 3 / 1 |
| tidal | generalist, 12 random patterns (held out) | 114.0 | 7.2 | 6.9 (n=4) | 5.9 to 8.6 | -3.9% | 0 / 4 / 0 |
| rush_hour | generalist, 12 random patterns (held out) | 138.3 | 126.6 | 137.6 (n=4) | 128.3 to 145.1 | +8.7% | 0 / 1 / 3 |
| low_traffic | generalist, 12 random patterns (held out) | 1.5 | 0.2 | 1.1 (n=4) | 0.9 to 1.2 | +414.8% | 0 / 4 / 0 |

Notes. "Tie or small" includes changes that are statistically significant but below the practical floor of 2 vehicles: in low_traffic the generalist's +415% is under one vehicle in absolute terms, but its wait per vehicle is 6.6 to 9.0 s against the rule's 1.6 s, so it is clearly worse in practice there. rush_hour_kt's -11.8% is about one vehicle on a base of 8.8 (wait per vehicle 18.7 s -> 16.2 to 17.0 s). Rule and agents were tuned and trained on selection seeds (20000+), never on these test seeds.
