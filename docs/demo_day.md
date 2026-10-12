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

## The three scenarios (what "traffic" means in each)
The junction has four roads (east, north, west, south). Every number below is "vehicles per hour arriving on each road", and every car goes straight through (no turns). Each demo run is 30 simulated minutes.

| Scenario | Arrivals per road | What it looks like | Why we test it |
|---|---|---|---|
| **Low traffic** | 120 per hour (a car about every 30 s) | Almost empty roads, no real queues. | Checks the controller does not do silly things when there is nothing to manage. |
| **Rush hour** | 900 per hour on every road (a car about every 4 s) | All four roads are busy at once. Queues build on every side and some roads fill up completely. | The hardest fair test: nobody can be left waiting forever, and the green time has to be shared well. |
| **Tidal** | North-south 1100 per hour and east-west 300 per hour for the first 15 minutes, then it flips: east-west 1100 and north-south 300 for the last 15 minutes | Heavy traffic one way, light the other way, then the roles swap, like a commuter flow into a city in the morning and out in the evening. | A fixed timer gives both directions equal green, so it wastes green on the quiet road while the busy road jams. This is where an adaptive controller should shine. |

(The "standard" scenario with 300 per hour on every road is the base setup the others were generated from; it is not in the demo.)

In the demo, say it in one line each:
- **Low traffic:** "Hardly any cars."
- **Rush hour:** "Everyone is on the road at once."
- **Tidal:** "Heavy one way, then the other, like a commute."

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

### The setting
SUMO is a traffic simulator: it moves every car second by second, with realistic acceleration, braking and gaps. Our Python code connects to it (through TraCI, SUMO's remote-control interface), reads what is happening at the junction, and tells the traffic light what to do. The junction has four roads and two light settings: north-south green, or east-west green.

### The agent's loop (every 5 simulated seconds)
1. **Look.** It reads 11 numbers: the queue on each of the 4 roads, how long the cars on each road have been waiting, which direction is green right now, and how long it has been green.
2. **Choose.** Two options: keep the current green, or switch to the other direction. If it switches, SUMO inserts a 3-second yellow automatically.
3. **Get scored.** Every simulated second costs "the number of cars waiting" (plus a small extra for cars held outside because a road is full). Switching costs a little extra, to stop it flickering. The reward is the negative of that cost, so fewer waiting cars means a better score.
4. **Learn.** It stores what happened and updates itself so it picks better choices next time.

### What DQN means
The agent learns a number called a **Q-value** for each choice: roughly "how good is this choice, counting all the waiting it will cause or avoid in the next few minutes". Both choices get a Q-value and the agent picks the higher one.
- A simple version stores Q-values in a lookup table (our first Q-table agent). That table only works when the situations are few and coarse.
- **DQN** replaces the table with a small neural network: 11 inputs, two hidden layers of 64 units, 2 outputs (one Q-value per choice). Because a network can handle numbers it has never seen exactly, it copes with the many different queue situations that really occur.

### Why a delay between action and result matters
Switching has an **immediate cost** (3 s yellow where nobody moves, plus the switch cost) but pays off **later** (the long queue clears). So the agent has to value the future, not just the next second. The setting that controls this is called **gamma**: higher means it looks further ahead. Raising it from 0.95 to 0.99 is what fixed our rush-hour results.

### The tricks that make DQN trainable
- **Replay buffer:** it keeps a memory of past steps and learns from random samples, not only the most recent ones, so consecutive similar steps do not mislead it.
- **Target network:** a slowly-updated copy of the network provides the learning targets, which keeps the learning from chasing itself.
- **Exploration:** early on it tries random choices (epsilon starts at 1.0) so it discovers what works, then gradually relies more on what it has learned (down to 0.05).
- All of this, including the network's learning step (backpropagation), is written by hand with NumPy, no RL libraries. We checked the gradients against a numerical test.

### How we train and test it fairly
- Training runs many 30-minute simulated episodes, each on different random traffic (a different seed).
- Every few episodes it is tested on seeds it has not trained on, and the best version is saved.
- Final results are measured on a **third** set of fresh seeds, because choosing the best of many runs makes results look better than they really are (we found a gap of about 134 vs 148 doing it wrong).
- Both controllers always get the same traffic (same seed) in a comparison, so one cannot get luckier traffic than the other.

### What the fixed-time controller is
It does not learn. It gives north-south green for 40 seconds, then east-west green for 40 seconds, forever, no matter how many cars are waiting. It is the standard yardstick: a real signal on a timer.

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
