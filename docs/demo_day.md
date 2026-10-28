# Demo day cheat sheet (v1.0)

## The story in three sentences
1. Most traffic lights run on a fixed timer. Nepal's first AI-enabled lights (Lalitpur, 2024) instead count vehicles and give green to the busier road.
2. We built that rule as a benchmark, and a learning controller (a DQN written from scratch, no RL libraries), and tested all three in the SUMO traffic simulator on 100 fresh runs per scenario.
3. The rule beats the fixed timer everywhere. The learned controller matches the rule, and in heavy, uneven traffic it is sometimes about 10% better, but not reliably. Being honest about that is the result.

## Setup (do it the day before, then again 15 minutes early)
**Either machine, same idea:** open a terminal in the project folder, activate the environment, check SUMO, start the demo.

Windows (PowerShell):
```powershell
cd $HOME\Desktop\adaptive-traffic-drl
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
sumo --version                         # must print a version
traffic-drl demo
```
Mac (Terminal):
```bash
cd ~/Downloads/adaptive-traffic-drl-with-git_2     # or wherever the project is
source .venv/bin/activate
sumo --version
traffic-drl demo
```
The page opens at http://localhost:8501 (type it in if it does not open itself).

Checklist
- [ ] Charger plugged in, sleep off, notifications off, nothing else heavy running.
- [ ] `sumo --version` works. If it does not: `pip install -e ".[sumo]"` (needs a decent connection, about 160 MB: do this at home).
- [ ] Run **Rush hour** once all the way through so everything is warm.
- [ ] **Backups:** (1) a screen recording of one good live run, (2) the **Test results** tab (needs no SUMO), (3) `figures/report/final_results.png` and `figures/report/regime_map.png` open as plain images.
- [ ] Check the projector early (Windows `Win + P`, Mac Displays settings).
- [ ] Second machine tested too (both laptops give identical numbers on the same seed, I checked: rush hour 143.3 / 129.0 / 126.1).

## What the three controllers are
- **Fixed-time:** north-south green for 40 s, then east-west for 40 s, forever. A normal timer.
- **Density rule:** counts the vehicles on each road and gives green to the busier road (with a minimum of 10 s and a maximum of 40 s). Like the Lalitpur lights. Its settings were tuned on separate seeds, not the test seeds.
- **DQN agent:** a small neural network that looks at queues, vehicle counts, waiting times and the current green every 5 simulated seconds and chooses keep or switch. It learned from experience in the simulator, started from the rule's demonstrations.

## Run order (sidebar: pick the scenario, DQN agent "Best for this scenario", seed 40000, speed 0.05)
Numbers below are what you will see (measured on seed 40000, the demo seed; mean vehicles waiting, lower is better). The app prints two sentences at the end: DQN against fixed, and DQN against the rule.

| # | Scenario | Fixed | Rule | DQN | What to point at | What to say |
|---|---|---|---|---|---|---|
| 1 | **Tidal** | 112.2 | 6.4 | 6.7 | Grey line climbs, orange and blue stay low. One road's queue piles up under the fixed timer. | "Heavy one way, then the other. The fixed timer cannot react. Both adaptive controllers cut the waiting by about 94%. The DQN matches the rule; it does not beat it." |
| 2 | **Rush hour** | 143.3 | 129.0 | 126.1 | All three close together, grey on top. | "Every road is busy. Both adaptive controllers are better than fixed, and the DQN and the rule are about level." |
| 3 | **Kathmandu mix, near capacity** | 12.0 | 9.1 | 8.0 | The mix of small and large vehicles, vehicles turning. | "More realistic traffic: motorcycles, buses and turns. The same story: adaptive beats fixed, DQN and rule are level." |
| 4 | **Heavy, uneven 8:1** | 319.2 | 122.4 | 104.9 | Orange line sits clearly above blue. | "Where traffic is heavy and very uneven, this run shows the DQN 14% better than the rule. But careful: in our 100-run test, only 1 of 4 trained agents was significantly better here. It depends on the training run." |
| 5 (optional) | **Kathmandu mix, peak** | 66.7 | 66.7 | 73.7 | All lines tangle; the junction is full. | "Slightly over capacity. When the junction is full, nobody can do much, and here the rule just behaves like the fixed timer. This is the honest failure case." |

Other scenarios if asked (seed 40000): **Low traffic** 1.5 / 0.2 / 0.5 (all near zero; the DQN switches lights more than needed, 121 times against 41). **Heavy uneven 2:1** 156.2 / 47.6 / 48.2. **Heavy uneven 4:1** 256.5 / 79.5 / 76.3. **Kathmandu tidal** 294.4 / 253.0 / 242.2.

Then the **Test results** tab: "Every number there is a mean of 100 test runs on traffic nobody trained or tuned on. Each dot in the figure is a separately trained agent, so you can see the spread, including the agents that lost."

## The numbers to remember (100 fresh-seed episodes, seeds 30000)
| What | Result |
|---|---|
| Rule against fixed timer | Better in all 16 demand patterns tried, by 20% to 98% less waiting |
| DQN against fixed timer (tidal) | About 94% less waiting (6.9 to 7.4 against 114.0) |
| DQN against fixed timer (rush hour) | About 10% less waiting (122 to 127 against 138.3) |
| DQN against the rule | Matches it. Heavy uneven traffic: 3 of 12 agents significantly better (5% to 11%), 2 worse, 7 tie or small |
| Kathmandu near capacity | DQN 7.6 to 8.0, rule 8.8, fixed 11.5 (9% to 14% below the rule, but only about one vehicle) |
| One model for every pattern | Not good enough yet; specialists are kept |

Live runs are a single episode, so they will not match these exactly. "Waiting" means vehicles stopped on the roads plus vehicles held outside because a road is full, averaged over the 30 simulated minutes.

## What the live panel shows
- **Vehicles waiting now** (right now, not an average), **vehicles served**, **signal switches**, **simulated time**.
- **Chart:** vehicles waiting over time. Grey = fixed, orange = density rule, blue = DQN. Lower is better.

## How it works (if asked)
- **The simulator.** SUMO moves every car second by second. Our Python code connects to it (TraCI), reads the junction and sets the lights. Two choices: north-south green or east-west green, with an automatic 3-second yellow.
- **The agent's loop, every 5 seconds.** Look at the state, choose keep or switch, get scored (every simulated second costs the number of cars waiting, plus a small cost for switching), and learn from it.
- **What DQN means.** It learns a number (Q-value) for each choice, roughly "how much waiting will this choice cause or avoid in the next few minutes", and picks the higher one. A small neural network replaces a lookup table so it copes with queue situations it has never seen exactly.
- **Why it was hard to train.** Early versions got good, then drifted and got worse. The fix was **learning from demonstrations**: we keep a frozen memory of the rule's decisions that is never overwritten, mix some of it into every training batch, and add a loss that stops the network drifting away from it, while normal learning still tries to improve on it.
- **Fair testing.** Same traffic for every controller. Settings tuned on one set of seeds, final results on a different set, 100 runs per cell, confidence intervals and significance tests. A change only counts as "better" if it is statistically significant and at least 5% and 2 vehicles.

## What we found along the way (good to mention)
- The first agent learned to cheat by flipping the light every second. We caught it from the switch count, changed the reward, and added a test.
- My first density rule counted only stopped vehicles and lost to the fixed timer. The mistake was mine; counting all vehicles, as a real detector does, fixed it.
- My first Kathmandu traffic was so heavy that no controller could help. Turning vehicles halve a single lane's capacity (about 1,800 vehicles an hour). I measured it and recalibrated.

## Honest limits (say these before they are asked)
- One junction, one lane per road, two light phases. Motorcycles queue in single file and do not weave between cars.
- The vehicle mix (62% motorcycles, 22% cars, 8% buses, 8% light goods) is an assumption from a source I still need to confirm.
- The DQN matches a tuned rule and only sometimes beats it, and that depends on the training run. The rule itself was tuned on cars-only traffic.
- One model for every traffic pattern does not work yet. Specialist agents per pattern are used.
- Both the rule and the DQN use vehicle counts, which in real life means detectors or cameras. This is not a "no sensors" solution.

## Likely questions
- **"So is the DQN better than the rule?"** About level. In some heavy, uneven cases an agent is about 10% better, but other trained agents tie or lose, so I cannot claim it is better in general.
- **"Why bother with a DQN then?"** It reached the rule's level without anyone hand-setting thresholds, and in some heavy cases it did better. The rule needs its settings tuned by hand for each junction; the agent learns them from simulation. The cost is a training process that needs care.
- **"Why a fixed timer as a baseline?"** It is the standard and what many junctions run. The rule is the harder baseline, because it is what Nepal is actually piloting.
- **"Why does it not win at rush hour or peak?"** When every road is full, any sensible timing moves the same cars. That is my explanation, not proven.
- **"Is it realistic?"** The simulator is a standard one, but the junction is simplified. The Kathmandu scenarios add motorcycles, buses and turns, with an assumed mix.
- **"Could it run in a real city?"** Not claimed. It is a simulation study; the next step would be real traffic counts and a multi-junction network.
- **"What would you do next?"** Multi-lane junctions with motorcycle filtering, real counts to calibrate the demand, a model that generalises across traffic patterns, and several junctions together.

## If something breaks
- Live panel shows an error: say "the simulator did not start on this machine", switch to the **Test results** tab (works without SUMO) and play the screen recording.
- Page will not open: show `figures/report/final_results.png`, `figures/report/regime_map.png` and the recording.
- Do not use `scripts/preview_demo.py` as a demo: its numbers are fake.
