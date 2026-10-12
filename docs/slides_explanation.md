# Slide-by-slide explanation

Deck: "Adaptive Traffic Signal Control" (6 slides). For each slide: what is on it, what to say, why it is there, and a question you might get.

All numbers come from the fresh-seed tests (10 runs per scenario, seeds 30000, 30 simulated minutes each). "Waiting" means the average number of vehicles waiting over the run (stopped on the roads plus held outside because the road is full). Lower is better.

---

## Slide 1 — Cover: "Teaching a traffic light to learn"

**On the slide:** the title, one line describing the project, your name and your supervisor's, and a drawing of a four-way junction (blue squares are waiting cars, green/red dots are the lights).

**What to say (about 20 seconds):**
"My project is about a traffic light that learns. Instead of a fixed timer, it looks at how many cars are waiting and decides which direction gets green. I trained it in a traffic simulator and compared it with a normal fixed timer."

**Why it is there:** to set the one-sentence idea before any detail.

**Possible question:** "What does 'learns' mean here?" It tries actions in the simulator, gets a score (fewer waiting cars is better), and adjusts itself to score higher. See slide 3.

---

## Slide 2 — The problem: "A fixed timer cannot see the traffic"

**On the slide:** two cards side by side. Left, the usual way: a fixed timer gives every direction the same green, whatever is happening, for example north-south green but empty while 11 cars wait on east-west. Right, our idea: a controller that looks at the queues and learns which direction should get green.

**What to say (about 40 seconds):**
"Most lights run on a timer. If one road is empty it still gets its full green while the other road jams. Our idea is to let the light see the queues and decide. The goal is simple: fewer vehicles waiting, for the same traffic."

**Why it is there:** it shows the problem we are solving and what the project does differently. The fixed timer is also what we compare against: 40 seconds of green for each direction, forever.

**Possible questions:**
- "Don't real lights already adapt?" Some do (actuated lights use sensors). We have not compared against one yet; it is a planned next step. Our baseline is the plain fixed timer.
- "Where does the example with 11 cars come from?" It is an illustrative picture of the problem, not a measured result.

---

## Slide 3 — How the agent works: look, choose, score, learn

**On the slide:** four numbered cards and one line underneath.
1. **Look:** the queue and waiting time on each road, and which direction is green.
2. **Choose:** keep the current green or switch (a yellow light is added automatically).
3. **Score:** fewer waiting cars means a better reward; each switch costs a little.
4. **Learn:** a neural network updates itself so good choices score higher next time.

Underneath: it repeats every 5 simulated seconds, and the method is a Deep Q-Network written from scratch with no reinforcement-learning libraries.

**What to say (about 60 seconds):**
"Every 5 simulated seconds the agent looks at the junction: how long the queue is on each road, how long cars have waited, which direction is green. It chooses between keeping the green and switching. It is scored on how many cars end up waiting, with a small cost for switching so it does not flicker. Then it learns from that. The learning part is a neural network, a DQN, that I wrote myself, including the learning step."

**Why it is there:** to explain the method in plain terms. A DQN learns a number for each choice (roughly "how much waiting will this choice cause or avoid in the next few minutes") and picks the better one.

**Possible questions:**
- "Why a neural network and not a table?" A table needs the queue lengths grouped into coarse buckets. A network can use the exact numbers and handle situations it has not seen exactly. We built a table version first (Q-table) as a warm-up.
- "Why 5 seconds?" Deciding every second let the agent flip the light constantly and cheat the score. Five seconds acts as a minimum green.
- "What is the cheat?" See slide 6.

---

## Slide 4 — How we tested it

**On the slide:** a table of the three scenarios and two lines about the fairness of the test.

| Scenario | Cars per hour, each road | What it looks like |
|---|---|---|
| Low traffic | 120 | Almost empty roads |
| Rush hour | 900 | Every road busy at once |
| Tidal | 1100 one way, 300 the other | Heavy one way, then it flips after 15 minutes |

Below: both controllers get exactly the same traffic in the SUMO simulator (30 simulated minutes per run), and results are averages of 10 runs on traffic the agent never saw during training.

**What to say (about 45 seconds):**
"I tested three kinds of traffic. Low traffic is almost empty roads. Rush hour has every road busy at once. Tidal is heavy one way and light the other, then it flips halfway, like a commute into and out of a city. The comparison is fair: both controllers face identical traffic, and the numbers come from runs the agent never trained on."

**Why it is there:** to show that the comparison is fair and covers different conditions, so the results on the next slide are meaningful.

**Possible questions:**
- "Why test on traffic it has not seen?" Otherwise it could just memorise. Also we found that picking the best of many training runs looks better than it really is, so the final numbers come from a third, fresh set of traffic.
- "Is the simulation realistic?" SUMO is a standard traffic simulator, but our setup is simplified: one junction, cars only go straight, no turns, no pedestrians.

---

## Slide 5 — Results: it clearly wins on tidal traffic

**On the slide:** three cards, each with the fixed-timer number, the DQN number (large) and a one-line verdict.

| Scenario | Fixed timer | DQN | Verdict |
|---|---|---|---|
| Tidal | 115 | 9.9 | About 91% fewer cars waiting |
| Rush hour | 139.7 | 140.8 | A tie, no gain |
| Low traffic | 1.5 | 0.5 | Both near zero |

Footnote: average vehicles waiting over a 30-minute run (lower is better), 10 runs per scenario on unseen traffic, using the best trained model for each scenario.

**What to say (about 60 seconds):**
"This is the main result. On tidal traffic the learned controller cuts the average number of waiting cars from 115 to about 10, around 91% fewer. On rush hour it matches the fixed timer, 140.8 against 139.7. That is a tie within noise, not a win. On low traffic both are close to zero. The agent also serves more vehicles per hour on tidal traffic, 2749 against 2445."

**Why it is there:** it is the evidence. The tie on rush hour is stated openly on purpose; a negative or mixed result, honestly reported, is a valid finding.

**Possible questions:**
- "Why does it tie on rush hour?" When every road is full, almost any sensible timing moves the same cars, so there is little to gain. That is our hypothesis; we have not proven it.
- "Why different models per scenario?" The model trained on a mix of all three is good on low traffic and tidal but still weak on rush hour. A single model for everything is the next step.
- "Is 140.8 vs 139.7 worse?" No. The difference is within the run-to-run variation (about 5 to 8 vehicles), so it is a tie.
- "Low traffic: is the DQN better?" Slightly lower waiting, but both are close to zero, and the DQN switches the lights far more often (121 times against 41), which would not be good in real life.

---

## Slide 6 — What we learned and what is next

**On the slide:** two columns.
- **What we learned:** the first agent cheated by flipping the light every second; we caught it by counting switches, fixed the reward and added a test. Letting the agent look further ahead (gamma 0.95 to 0.99) brought rush hour from about 200 down to about 140.
- **Limits and next steps:** it wins clearly only on uneven traffic and uses a separate model per scenario. Next: one model for every pattern, a smarter non-learning baseline for comparison, and the final report.

**What to say (about 45 seconds):**
"Two things stand out. First, a real bug: the first agent learned to cheat by flipping the light every second, because the score ignored the yellow time. We found it by tracking the number of switches, fixed it and added a test so it cannot come back. Second, the biggest improvement came from one setting, how far ahead the agent looks. The honest limits are that the clear win is on tidal traffic only, and we use one model per scenario. Next steps are a single model for all patterns, a stronger baseline called an actuated controller, and the final report."

**Why it is there:** it shows rigour (a bug found and fixed), a real finding (look-ahead matters), and an honest plan.

**Possible questions:**
- "What does gamma mean?" How far ahead the agent looks. Switching costs something now (yellow time, a switch penalty) but pays off later when the queue clears, so the agent has to value the future.
- "What is an actuated controller?" A traffic light that uses sensors to extend or cut green, but is not learned. It is a tougher baseline than a fixed timer.
- "Could this be used on a real road?" Not claimed. It is a research simulation of one junction.

---

## Timing

About 5 minutes in total if you stay close to the lines above: slide 1 about 20 s, slide 2 about 40 s, slide 3 about 60 s, slide 4 about 45 s, slide 5 about 60 s, slide 6 about 45 s. If you also show the live demo, do it between slides 4 and 5 or after slide 5, and use `docs/demo_day.md` for that part.
