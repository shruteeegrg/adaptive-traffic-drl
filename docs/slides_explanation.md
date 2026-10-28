# Slide-by-slide explanation (final results)

Six slides, about 6 to 7 minutes. Deck: https://claude.ai/artifact/8HT9y1burUpvbXnaAziDE6. The same notes are in each slide's speaker notes.
The one idea to leave the room with: **adaptive control clearly beats a fixed timer; a learned controller can match a tuned rule and sometimes beat it, but not reliably.**

## 1. Cover: Teaching a traffic light to learn
**On the slide:** title, subtitle, a drawing of the junction (blue squares are waiting cars, green and red dots are the lights).
**Say (15 s):** "I built a traffic light controller that learns from experience, and compared it with a normal fixed timer and with the vehicle-counting rule that Nepal is piloting, in a traffic simulator."

## 2. A fixed timer cannot see the traffic
**On the slide:** three cards: fixed timer, density rule (what Nepal is piloting), learned controller. The question at the bottom.
**Say (45 s):** "A normal light gives every direction the same green, even if one road is empty and the other is jammed. Nepal's first AI-enabled lights in Lalitpur count the vehicles and give green to the busier road. That is a much tougher thing to beat than a fixed timer, so I built that rule as a benchmark too. My idea is a controller that learns by trial and error. The real question is not whether it beats a fixed timer, which is easy, but when learning is worth it compared with a simple, well-tuned rule."
**If asked:** "Where does the rule come from?" It is modelled on the Lalitpur pilot as reported (Onlinekhabar, 2024); I could not see the real system's code, so it is my version of the idea, and its settings were tuned on separate seeds.

## 3. How the agent works
**On the slide:** four steps (look, choose, score, learn) and the parts: SUMO, environment, DQN agent, model file.
**Say (60 s):** "Every 5 simulated seconds the agent looks at the junction (queues, vehicle counts, waiting times, which direction is green), chooses to keep the green or switch, gets scored on how many cars are waiting, and learns. SUMO simulates the traffic, my environment turns it into a state and a reward, and the trained model is saved to a file the demo loads. The network is written from scratch in NumPy, including the learning step, with no reinforcement-learning library. What made training reliable was learning from demonstrations: the agent keeps a frozen memory of the rule's decisions and a loss that stops the network drifting away from them."
**If asked:** "What is a DQN?" It learns a number for each choice, roughly how much waiting that choice will cause or avoid over the next few minutes, and picks the higher one. A small neural network replaces a lookup table so it copes with queue situations it has never seen exactly.

## 4. How we tested it
**On the slide:** a table of three scenario groups and the five-step workflow (train and tune, select, test, compare, report).
**Say (50 s):** "Three groups of traffic: the original three, a grid of sixteen patterns from light to heavy and from even to very uneven, and Kathmandu-style traffic with motorcycles, buses and turns. The mix there is an assumption I still need to confirm against its source. I tune on one set of traffic, select on another, and test on a third, 100 runs per cell, with all three controllers on identical traffic. A change only counts as better if it is statistically significant and at least 5% and 2 vehicles. Every trained agent is reported, including the ones that tie or lose."
**If asked:** "Why 5% and 2 vehicles?" So a statistically significant but tiny difference is not presented as a win. I fixed the rule before seeing the results.

## 5. Results: the DQN matches a tuned rule
**On the slide:** three cards: adaptive against fixed (-94% on tidal), DQN against the rule (level), heavy uneven traffic (-5 to -11% for 3 of 12 agents).
**Say (90 s):** "Against a fixed timer both adaptive controllers win clearly: on tidal traffic waiting falls from 114 to about 7, 94% less, and about 10% less on rush hour. But the fair comparison is the density rule, and there the DQN is level. Across 32 specialist agents, 3 were significantly better, 3 significantly worse and 26 were ties or small differences. In heavy, uneven traffic 3 of 12 agents beat the rule by 5 to 11%, but others tied or lost, so I cannot claim the DQN is better in general. And one model for every pattern did not work: on traffic it had not seen, it lost to the rule."
**Numbers to remember:** tidal 114.0 / 7.2 / 6.9 to 7.4 (fixed / rule / DQN); rush hour 138.3 / 126.6 / 122.2 to 126.6; 800 per road at 8:1, 321.9 / 119.0 / 105.6 to 119.0.
**If asked:** "So why use a DQN?" It reached the rule's level without hand-set thresholds, and sometimes did better; the cost is a training process that needs care and several agents. "Why does the rule tie at the peak?" When both axes are always loaded it behaves like the fixed timer, and nobody can do much when the junction is full.
**Evidence for the room:** the live demo's Test results tab shows the table and a dot plot with every trained agent.

## 6. What we learned and what is next
**On the slide:** two columns: what we learned; limits and next steps.
**Say (45 s):** "Three lessons. The baseline decides how good a result looks: a tuned rule beat every early version of my DQN. Learning from the rule's demonstrations made the DQN reliable. And my own mistakes were the most useful: an agent that cheated by flipping the light, and a rule that counted the wrong vehicles. Limits: one junction with one lane per road, an assumed vehicle mix, a DQN that does not reliably beat the rule, and no single model for every pattern. Next: multi-lane junctions where motorcycles can filter, real traffic counts, and several junctions together."
**If asked:** "Could it run in a real city?" Not claimed; it is a simulation study. The next step would be real counts and a network of junctions.

## Timing and delivery
- About 6 to 7 minutes on the slides, then the live demo (see `docs/demo_day.md`), then questions.
- Say the limits yourself, before anyone asks. The honest result is the strength of the project.
