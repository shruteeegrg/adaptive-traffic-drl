# Demo day cheat sheet

## Before you start (10 minutes early, on the Windows laptop)
1. Plug in the charger. Sleep is already off (`powercfg /change standby-timeout-ac 0`).
2. Open PowerShell in the project folder and activate the venv, then:
   ```powershell
   git pull origin main
   traffic-drl demo
   ```
3. Run **one** scenario all the way through, so everything is warm. Close nothing else heavy (no sweeps).
4. Have a backup ready: a screen recording of one tidal run, plus `figures/compare_best.png` open as a plain image.
5. Check the projector / screen early (Windows: `Win + P`).

## The one-sentence version
We built a traffic-light controller that learns by trial and error (a DQN, written from scratch, no RL libraries) and compared it with a normal fixed timer in the SUMO traffic simulator.

## Run order (sidebar: scenario, checkpoint "Best for this scenario", seed 40000, speed 0.05)
| # | Scenario | What to point at | What to say |
|---|---|---|---|
| 1 | **Tidal** | Grey line climbs, blue stays low. Queue squares pile up on one road under the fixed timer. | "Traffic is heavy one way, then the other. The fixed timer cannot react, the DQN does. About 91% fewer vehicles waiting." |
| 2 | **Rush hour** | The two lines sit on top of each other. | "Every road is full. The fixed timer is already close to the best possible, and the DQN matches it. We did not beat it here." |
| 3 | **Low traffic** | Both near zero. | "Almost no cars, so both do fine. The DQN switches the lights more often than it needs to, a weakness we know about." |

Then the **Test results** tab: "These are averages over 10 test runs on traffic the agent never trained on, so they do not depend on one lucky run."

## The numbers to remember (10 fresh-seed episodes, seeds 30000)
| Scenario | Fixed-time | DQN | In words |
|---|---|---|---|
| Tidal | 115 | 9.9 | DQN far better (about -91%), and serves more vehicles/hour (2749 vs 2445) |
| Rush hour | 139.7 | 140.8 | A tie |
| Low traffic | 1.5 | 0.5 | Both near zero; DQN switches 121 times vs 41 |

"Waiting" = average number of vehicles waiting (stopped on the roads + held outside) over the 30-minute run. Lower is better.

Live runs use seed 40000 and are a single episode, so they will not match the table exactly. Rush hour on one run was 138.0 (DQN) vs 143.3 (fixed): "about the same", the app says so itself.

My live numbers today (fill in):
- Tidal: fixed ____  DQN ____
- Rush hour: fixed 143.3  DQN 138.0
- Low traffic: fixed ____  DQN ____

## What the live panel shows
- **Vehicles waiting now:** cars stopped on the four roads + cars held outside because the road is full (right now, not an average).
- **Vehicles served:** cars that finished their trip so far.
- **Signal switches:** how many times the light changed direction.
- **Simulated time:** progress through the 30 simulated minutes (a run takes seconds, not 30 minutes).
- **Chart:** vehicles waiting over time. Grey = fixed timer, blue = DQN. Lower line is better.

## How it works (if asked)
- Every 5 simulated seconds the agent sees the junction (queue and waiting time per road, which direction is green, how long) and chooses: keep green or switch. SUMO adds a 3 s yellow when it switches.
- It is rewarded for fewer waiting cars, and charged a small cost per switch.
- DQN = Q-learning with a neural network (11 inputs, two hidden layers of 64, 2 outputs), replay buffer and target network. Hand-written, including backpropagation (checked against a numerical gradient).
- Fair test: both controllers get the same traffic (same seed), test seeds are never used in training.

## What we found along the way (good to mention)
- First version learned to cheat by flipping the light every second. We caught it because we tracked the switch count, fixed the reward, and added a test.
- Rush hour was clearly worse than the fixed timer (about 200) until we raised the discount factor gamma from 0.95 to 0.99: waiting dropped to about 140 and results became much more consistent across seeds.
- We picked checkpoints on one set of seeds and confirmed on fresh seeds, because picking the best of many runs looks better than it is.

## Honest limits (say these before they are asked)
- It clearly wins on tidal traffic only. On rush hour it ties; on low traffic both are near zero.
- It uses a separate model per traffic pattern. One model for everything is not solved (the mixed model is still weak on rush hour).
- One simulated junction, cars go straight only, no turns, no pedestrians.
- Training is sensitive to the random seed and the machine; results vary between runs.

## Likely questions
- **"Why not just use the DQN everywhere?"** It only wins where traffic is uneven. Where the fixed timer is already near-optimal there is nothing to gain.
- **"Why does it tie on rush hour?"** When every road is saturated, any sensible timing moves the same cars. Our hypothesis, not proven.
- **"Is the SUMO simulation realistic?"** It is a standard traffic simulator, but our setup is simplified (one junction, straight-through traffic).
- **"What is next?"** An actuated-controller baseline (a smarter non-learning comparison), turning movements, one model for all patterns, and the final report.
- **"Could it work in a real city?"** Not claimed. It is a research simulation.

## If something breaks
- Live tab shows an error: say "the simulator did not start on this machine", switch to the **Test results** tab (works without SUMO) and show the backup recording.
- App will not open at all: show `figures/compare_best.png` and the recording.
- Do NOT run `scripts/preview_demo.py` as a demo: its numbers are fake.
