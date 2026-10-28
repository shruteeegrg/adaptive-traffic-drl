# Final Report: Adaptive Traffic Signal Control System using Deep Reinforcement Learning

Shruti Gurung (2337686) · CIS017-3 · University of Bedfordshire · Supervisor: Pawan KC

**Status: first full draft, written in Week 7 from the saved results (`docs/results_final.md`) and the project logs.** Sections 3 to 7 are drafted
from evidence in the repository. Section 2 (literature review) is a structured skeleton only, because it needs the critical synthesis my supervisor
asked for. Everything in `[square brackets]` still needs your decision, a source or your own words.

Open items before this can be submitted:
- [ ] Section 2: write the critical synthesis (see the plan in 2.3). Do not copy claims about papers from this draft; read each paper and check.
- [ ] Verify Hester et al. (2018), van Hasselt et al. (2016), the Rasheed et al. (2020) page numbers, the Pant paper's year and volume, and the source of the vehicle mix (MOPIT 2023) against the originals.
- [ ] Requirements (3.7): list the numbered functional and non-functional requirements from the contextual report and link each to a test or result.
- [ ] Fix the survey figures in the contextual report before reusing them (see `docs/completeness_assessment.md`).
- [ ] Add the AI-assistance statement if the university's policy requires one (your decision, not added here).

---

## Abstract (draft)

Fixed-time traffic signals give every direction the same green time regardless of demand. This project builds an adaptive controller for a
single four-way junction in the SUMO traffic simulator: a Deep Q-Network (DQN) written from scratch in NumPy, with no reinforcement-learning
libraries. It is compared with a fixed timer and with a density-responsive rule of the kind used in Nepal's first AI-enabled signals
(Lalitpur, 2024). Every comparison uses identical traffic, 100 fresh-seed episodes, confidence intervals and significance tests, and a decision
rule fixed in advance. The density rule beats the fixed timer in all 16 demand patterns tried, by 20% to 98%. A DQN trained from the rule's
demonstrations matches the rule in every scenario and, in heavy, uneven traffic, 3 of 12 trained agents were significantly better (5% to 11%),
but 2 were worse, so the benefit depends on the training run. A single model for all traffic patterns did not match the rule on unseen
traffic. The work contributes a fair benchmark method, a calibrated Kathmandu-style scenario set, an honest map of where learning helps, and an
installable product with a live demo.

---

## 1. Introduction

### 1.1 Problem and motivation
Most signalised junctions run on a fixed timer: every direction gets the same green time whether its road is empty or jammed. In Kathmandu this
is a visible problem [add verified facts about Kathmandu congestion and signal reliability, with sources]. Nepal's first AI-enabled signals,
five lights from Kupondole to Jawalakhel in Lalitpur, count vehicles and favour the busier road (Onlinekhabar, 2024) [check the article for the
exact wording and date]. That is a much stronger comparison point than a fixed timer, and it shapes the question this report asks.

### 1.2 Aim, question and objectives
The proposal's aim was to show that an adaptive agent reduces congestion compared with a fixed timer, through four objectives:
O1 simulate a realistic intersection in SUMO; O2 design a custom neural network as the Q-value approximator; O3 implement the training loop
(action selection, reward, backpropagation) from scratch; O4 show that the agent reduces congestion metrics compared with a fixed timer.

Early results made O4 too easy to satisfy: any adaptive rule beats a fixed timer on uneven traffic. The question became:
**when is a learned signal controller worth it, compared with a simple, well-tuned rule?**

### 1.3 Contributions
1. A fair benchmark method: identical traffic for every controller, separate seeds for tuning and testing, 100 episodes per cell, confidence
   intervals, Welch and paired t-tests, effect size, and a practical-significance rule (Section 3.6).
2. A density-responsive baseline tuned on separate seeds, and a regime map showing where adaptive control helps (Section 5.2).
3. A from-scratch NumPy DQN with learning from demonstrations, and a diagnosis of why plain DQN training was unstable (Section 5.3).
4. Kathmandu-style scenarios (motorcycle-heavy fleet, turning vehicles) calibrated to the junction's measured capacity (Section 5.4).
5. An installable, config-driven product (`traffic_drl`, CLI `traffic-drl`) with a live demo of three controllers on nine scenarios.

### 1.4 Structure
Section 2 reviews the background; Section 3 gives requirements and method; Section 4 the artefact; Section 5 the results; Section 6 the
evaluation and limits; Section 7 the conclusions.

---

## 2. Background and literature review

**[TODO: critical synthesis. This section is a skeleton.]**

### 2.1 Fixed-time, actuated and density-responsive control
[Define fixed-time, vehicle-actuated and density-responsive control. Cite a traffic-engineering source. Explain why the density rule is the
right baseline here, using the Lalitpur pilot (Onlinekhabar, 2024).]

### 2.2 Reinforcement learning foundations
[Q-learning and the Bellman target (Sutton and Barto, 2018); DQN with replay and target network (Mnih et al., 2015); Double DQN
(van Hasselt et al., 2016); learning from demonstrations (Hester et al., 2018). One paragraph each, tied to a design choice in Section 3.3.]

### 2.3 Deep RL for traffic signal control: how to turn the summary into a synthesis
The review by Rasheed et al. (2020) and the Kathmandu framework paper by Pant (2024) are in hand. For each study you read, fill one row, then
write about the columns instead of about the papers one by one:

| Study | State | Action | Reward | Baseline used | Scenarios (traffic type) | Evaluation (runs, seeds, statistics) | Result claimed |
|---|---|---|---|---|---|---|---|
| [ ] | | | | | | | |

Questions the table should let you answer, each with citations [only write the answer after checking the papers]:
- Which baselines do studies compare with, and how many include a tuned actuated or density rule?
- Do state and reward designs agree, and does the choice seem to change the result?
- How many report several seeds, confidence intervals or any significance test?
- How realistic is the traffic (vehicle mix, turns, demand pattern)?
- Where do studies disagree, and what would explain it?
Then link each answer to this project's evidence: for example that a tuned rule is a strong baseline (Section 5.1), and that training stability
and seed variance mattered (Section 5.3).

### 2.4 The Kathmandu context
[Pant (2024), "Framework for AI-Driven Traffic Management in Kathmandu", Far Western Review, pp. 130-141: a SUMO-based study; check its method
and whether its reported improvement (up to 25%) has a baseline and a measurement you can verify. Onlinekhabar (2024): the Lalitpur pilot;
treat the police claims about waiting times as claims, not data.]

### 2.5 The gap
[Draft after 2.3: the gap this project addresses is a fair, statistically tested comparison of a from-scratch DQN with a tuned density rule on
Kathmandu-style traffic.]

---

## 3. Requirements and methodology

### 3.1 Method
The work was incremental, to limit the convergence risk named in the proposal: a Q-table on a simplified problem first, then the neural network
and DQN on the full intersection, then a benchmark, then realism. Experiments had a written question first; from the benchmark onwards the
decision rule was fixed before the results came in. The weekly logs (`logs/`) record the order, including dead ends.

### 3.2 Simulation environment
- **Junction.** One four-way junction in SUMO (network `configs/intersection.net.xml`), one lane per road, two signal phases (north-south green,
  east-west green) with a 3 s yellow inserted on every switch. Approach roads are about 92.8 m, which holds about 12 cars.
- **Control.** The environment talks to SUMO through TraCI. The agent decides every 5 simulated seconds: keep the current green or switch.
  An episode is 1,800 simulated seconds (30 minutes).
- **Backlog.** When a road is full, further vehicles wait outside the network. They are counted (backlog), because queue length alone hides them.
- **Seeds.** Each episode uses a different SUMO seed.

### 3.3 Agent design
- **State (final agents, 15 inputs).** Queue (stopped vehicles) on each road, the number of vehicles on each road, the waiting time on each road,
  the current phase (one-hot) and the time in the current phase.
- **Action.** Two: keep or switch.
- **Reward.** The negative of a cost charged for every simulated second (yellow included): stopped vehicles, plus 0.1 per vehicle in the backlog,
  plus a switch penalty of 5, divided by 50. Charging per second instead of per decision removed an exploit (Section 5.3).
- **Network and learning.** Two hidden layers of 64 units, written in NumPy with backpropagation checked against a numerical gradient; Adam,
  Huber loss, replay buffer (20,000), target network updated softly (rate 0.005), gradient clipping (5), learning rate 5e-4 decaying by 0.985
  per episode, discount 0.99, epsilon from 1.0 to 0.05, Double DQN.
- **Learning from demonstrations (DQfD-style).** First, 20 episodes of the density rule with 20% action noise provide a teacher; the rule's own
  decisions go into a frozen buffer that is never overwritten, and 25% of every training batch is drawn from it. A large-margin loss (margin 1.0)
  keeps the rule's action ranked above the alternative on those rows. Ordinary Q-learning continues on the rest.

### 3.4 Baselines
- **Fixed timer:** 40 s per direction (a 30 s variant was also tuned and is no better).
- **Density rule:** count all vehicles on each road (as a detector would); keep green at least 10 s; switch when the current axis is empty, when
  the other axis holds more than 4 times as many vehicles, or at 40 s if the other axis has vehicles waiting. Tuned on the selection seeds.

### 3.5 Scenarios
| Family | Demand per road (veh/h) | Purpose |
|---|---|---|
| Original three (cars, straight) | low 120; rush hour 900; tidal 1100 / 300 flipping every 15 minutes | Basic checks |
| 16-pattern grid (cars) | mean 200 to 800; north-south to east-west ratio 1:1 to 8:1 | Regime map |
| Kathmandu-style mix | 120 to 500 (and a tidal pattern) | Motorcycles, buses, light goods, 15% left and 15% right turns |
| 12 randomised patterns | heavier axis 300 to 1300; balanced, uneven and flipping | Training a single model |

The vehicle mix (62% motorcycles, 22% cars, 8% buses, 8% light goods) is an assumption [source: MOPIT 2023, to verify]. Motorcycles queue in single
file (no sublane model), so they take less road but do not filter between vehicles.

### 3.6 Evaluation protocol
- **Seeds.** Training, tuning and selection (20000s), periodic evaluation (10000s), final tests (30000s), demo (40000s). Nothing is tuned or
  chosen on the final-test seeds.
- **Metrics.** Primary: mean total waiting (vehicles stopped on the roads plus vehicles in the backlog, averaged over the episode). Secondary:
  waiting per vehicle (which ignores the backlog and flatters policies that hold vehicles back in saturation), throughput per hour, switches.
- **Statistics.** 100 episodes per cell; every controller sees identical traffic; mean with 95% confidence interval; Welch and paired t-tests;
  Cohen's d. The t-tests are written without a statistics library and checked against numerical integration.
- **Decision rule (fixed in advance).** A controller is "better" only if p < 0.05 and the change is at least 5% of the reference and at least 2
  vehicles. A significant change below that threshold is "small".
- **All trained agents are reported,** four independent seeds per scenario, not only the best.

### 3.7 Requirements
[TODO: list the numbered functional and non-functional requirements from the contextual report and link each to a test or result. The
assessment in `docs/completeness_assessment.md` has the comparison and the gaps.]

---

## 4. Artefact design and implementation
The deliverable is an installable, config-driven Python package, not a script.
- **Package `traffic_drl`:** environment wrapper (TraCI), feature and reward design, NumPy neural network, DQN and Q-table agents, replay buffer,
  training and sweep loops, baselines (fixed timer, density rule), statistics, comparison, plots, and a Streamlit demo.
- **Command line `traffic-drl`:** `train`, `sweep`, `evaluate`, `compare`, `run`, `plot`, `demo`, `env-check`.
- **Configuration:** YAML files with inheritance (`extends:`) for the intersection, agents and scenarios; scenario route files are generated by
  scripts (fleet, turns, randomised patterns, grid).
- **Testing:** about 140 automated tests, including the neural network gradient check, the reward exploit regression, the statistics, the
  scenario generators checked against the network's connections, and the demo app driven headlessly. A fake TraCI lets most tests run without
  SUMO; real-simulator checks were run on Windows and on a Mac, giving identical results on the same seed.
- **Reproducibility:** results tables and figures are rebuilt from saved files (`scripts/build_results.py`); the final agents are in `models/`
  with a manifest; the release is tagged `v1.0`. A clean install on a fresh machine found and fixed three problems (a wrong controller name in the
  demo, an unused `torch` dependency, SUMO missing from the install).
- **Design diagrams** (business context, use case, class, data flow, entity-relationship, functional and system architecture, sequence, activity,
  workflow) are in `docs/diagrams` and in the reflective report's Appendix A. [Include the ones you want in this report's appendix.]
- **Demo:** three controllers (fixed, density rule, DQN) side by side on nine scenarios, with plain-language verdicts.

---

## 5. Results

### 5.1 Benchmark: learned agents against the tuned rule
Mean total waiting, 100 fresh-seed episodes per cell, identical traffic (lower is better). The DQN column is the range of four independently
trained agents. The full per-agent table is `docs/results_final.md`; the figure is `figures/report/final_results.png`.

| Scenario | Fixed timer | Density rule | DQN agents | DQN against the rule |
|---|---|---|---|---|
| Tidal | 114.0 | 7.2 | 6.9 to 7.4 | 4 ties or small |
| Rush hour | 138.3 | 126.6 | 122.2 to 126.6 | 4 ties or small (−3.4% to +0.1%) |
| Heavy, uneven 2:1 (800 per road on average) | 155.4 | 48.2 | 47.0 to 50.7 | 3 ties, 1 worse |
| Heavy, uneven 4:1 | 254.6 | 75.8 | 68.4 to 80.4 | 2 better, 1 tie, 1 worse |
| Heavy, uneven 8:1 | 321.9 | 119.0 | 105.6 to 119.0 | 1 better, 3 ties or small |
| Kathmandu mix, tidal | 297.0 | 237.0 | 234.2 to 243.5 | 4 ties or small |
| Kathmandu mix, near capacity (400) | 11.5 | 8.8 | 7.6 to 8.0 | 4 small (−9% to −14%, about one vehicle) |
| Kathmandu mix, peak (500) | 72.8 | 68.9 | 67.2 to 72.7 | 3 ties or small, 1 worse |

Across the 32 specialist agents: 3 significantly better than the rule, 3 significantly worse, 26 ties or small differences. Against the fixed
timer both adaptive controllers win wherever the demand gives them something to work with.

### 5.2 Regime map: where does adaptive control help?
Fixed timer against the tuned rule over 4 demand levels and 4 unevenness levels (30 episodes per cell, `figures/report/regime_map.png`). The rule is
better in all 16 cells: 82% to 92% less waiting at 200 per road; 41% to 75% at 400; 36% to 98% at 600; 20% to 70% at 800. The smallest gains are
at balanced demand near capacity (800, even: 43.5 to 34.9); the largest where load is high and uneven (600 at 8:1: 151.0 to 3.4). The learned
agents were then trained where the rule leaves the most waiting (the heavy, uneven row), which is where the 3 significant improvements were found.

### 5.3 Training: from unstable to reliable
- **A reward exploit.** The first agent flipped the light on every decision (about 450 switches per episode) because cost was charged per decision.
  Charging per simulated second fixed it, and a regression test now guards it.
- **Discount factor.** Raising gamma from 0.95 to 0.99 cut rush-hour waiting from about 200 to about 140 and made seeds consistent.
- **A tougher baseline.** The tuned rule beat every early DQN: tidal 7.2 against 10.1, rush hour 126.6 against 139.8, and an agent trained on rush
  hour never switched on light traffic.
- **Instability.** Agents were good early and worse later. Giving the DQN the rule's vehicle counts, Double DQN, soft target updates, gradient
  clipping and learning-rate decay stabilised training (rush hour 133 to 149 across seeds, against 129 to 256 before) but did not reach the rule.
  Adding the rule's experience to the replay buffer kept 2 of 4 tidal runs good for all 120 episodes.
- **Learning from demonstrations.** Keeping the rule's decisions in a frozen buffer, with a margin loss, made all 16 runs on tidal and rush hour
  end at or below the rule on the selection seeds (tidal 6.3 to 7.5 against 7.3; rush hour 116 to 126 against 127.7), where the earlier recipes
  gave 10 to 37 on tidal. The 100-episode test confirmed it (Section 5.1). In the cars-only rush-hour sweep the learning stage improved on the
  imitation (127 to 141 right after the teacher copy, 119 to 123 later); in the generalist it did not (5.5).

### 5.4 Kathmandu-style traffic
My first demand levels (900 and 1,100 vehicles per hour per road) overloaded the junction: throughput stayed near 1,830 vehicles per hour and the rule
behaved exactly like the fixed timer. Diagnostic scenarios showed that turning vehicles halve a single lane's capacity: cars going straight 3,025
vehicles per hour, mixed fleet going straight 3,232, cars with 15% + 15% turns 1,650. The demand was recalibrated to the measured capacity (about
1,800 vehicles per hour in total, about 450 per road). With turns, at 300 and 400 per road the rule beats the fixed timer; at 500 and 600 they tie
(`results_compare_kt_calib`). Results for the recalibrated set are in Section 5.1.

### 5.5 One model for every pattern
A single model trained on 12 randomised demand patterns was tested on three scenarios it never saw (`results_compare_general`): tidal 5.9 to 8.6
(rule 7.2), rush hour 128.3 to 145.1 (rule 126.6), light traffic 0.9 to 1.2 (rule 0.2; waiting per vehicle 6.6 to 9.0 s against 1.6 s). Of 12
agents, none was better than the rule and 3 were worse. In all four runs the best checkpoint was the one right after copying the rule, so
further training added nothing. This is a negative result; one specialist model per scenario is kept.

### 5.6 Live demonstration
The demo reproduces the benchmark on a single episode: on rush hour (seed 40000) the three controllers waited 143.3 (fixed), 129.0 (rule) and 126.1
(DQN), identically on Windows and on a Mac.

---

## 6. Evaluation and discussion

### 6.1 Against the objectives
- **O1** A SUMO junction with three demand scenarios, a 16-pattern grid and Kathmandu-style traffic: met, with the limits in 6.3.
- **O2** A custom network: met, 64-64 NumPy MLP with gradient-checked backpropagation.
- **O3** Training loop from scratch: met, including replay, target network, Double DQN and learning from demonstrations.
- **O4** The agent reduces congestion compared with a fixed timer: met wherever the demand allows (about 94% on tidal, about 10% on rush hour). Against
  a tuned density rule, the agent matches it and does not reliably beat it.

### 6.2 When is learning worth it?
- A tuned density rule captures almost all of the benefit of adaptive control. It needs only vehicle counts and a few settings tuned for the junction.
- A learned controller can reach the rule's level without anyone hand-setting thresholds, and in heavy, uneven traffic it sometimes does better
  (3 of 12 agents, 5% to 11%), but the result depends on the training run, so several agents must be trained and all reported.
- Under saturation (the peak scenario) no controller helps much; under very light traffic everything is near zero.
- [Link to the literature once Section 2.3 is written: do other studies that compare with a tuned rule find the same?]

### 6.3 Limitations and threats to validity
- **One junction, one lane per road, two phases.** Real Kathmandu junctions are larger. Motorcycles queue in single file; the vehicle mix is an assumption.
- **The rule was tuned on cars-only traffic** and not re-tuned on the Kathmandu-style scenarios; this may under- or over-state its strength there.
- **The DQN starts from the rule's demonstrations,** so matching it is expected; the evidence for learning is the cases where it goes past it, and
  those are few and seed-dependent.
- **Small number of agents** (four per scenario) and one training recipe; conclusions about "reliability" are tentative.
- **Metrics.** Mean total waiting includes the backlog; waiting per vehicle does not and can mislead in saturation. Both use simulated time.
- **Both controllers use vehicle counts,** which in practice need detectors or cameras. This is not a "no sensors" result.
- **Simulation is not reality.** No real traffic data were used to calibrate demand [add if any are obtained].
- **Platform.** Results were identical on Windows and Mac for the same seed in the demo; an earlier convergence test on a toy problem differed by
  platform, and its root cause was not found.

### 6.4 Project management
[Summarise from `logs/` and the weekly updates: ahead of plan on the build, extra time on the evaluation question, the tools used to keep the
work honest (separate seeds, fixed decision rule, regression tests, clean-install checks). Keep it short and link to the reflective report.]

---

## 7. Conclusions and further work
The project meets its core objectives and answers a sharper question than the proposal asked. Adaptive control clearly beats a fixed timer where
demand gives it room; a tuned density rule gets almost all of that benefit; and a from-scratch DQN trained from the rule's demonstrations matches
the rule and sometimes beats it by about 10% in heavy, uneven traffic, but not reliably, and not as a single model for every pattern.

Further work: multi-lane junctions with motorcycle filtering (SUMO's sublane model); calibrating demand from real counts; a model that generalises
across patterns; and several junctions together. [Add anything the supervisor suggests.]

---

## References
[Format all references consistently (Harvard) and check each against the original.]

- Hester, T. et al. (2018) 'Deep Q-learning from demonstrations', *Proceedings of the AAAI Conference on Artificial Intelligence*, 32(1). [check]
- Lopez, P.A. et al. (2018) 'Microscopic Traffic Simulation using SUMO', *2018 21st International Conference on Intelligent Transportation Systems (ITSC)*, pp. 2575-2582.
- Mnih, V. et al. (2015) 'Human-level control through deep reinforcement learning', *Nature*, 518(7540), pp. 529-533.
- Onlinekhabar (2024) *Nepal's first intelligent traffic lights operational from Kupondole to Jawalakhel*. Available at: https://english.onlinekhabar.com/nepals-first-intelligent-traffic-lights-operational-from-kupondole-to-jawalakhel.html (Accessed: [date]).
- Pant, K. (2024) 'Framework for AI-Driven Traffic Management in Kathmandu', *Far Western Review*, pp. 130-141. [check year, volume and issue]
- Rasheed, F. et al. (2020) 'Deep Reinforcement Learning for Traffic Signal Control: A Review', *IEEE Access*, 8, pp. 208032-208051. [the pages in my notes disagree with the contextual report: check]
- Sutton, R.S. and Barto, A.G. (2018) *Reinforcement Learning: An Introduction*. 2nd edn. Cambridge, MA: MIT Press.
- SUMO Documentation (2024) *TraCI: Traffic Control Interface*. Available at: https://sumo.dlr.de/docs/TraCI.html (Accessed: 27 February 2026).
- van Hasselt, H., Guez, A. and Silver, D. (2016) 'Deep reinforcement learning with double Q-learning', *Proceedings of the AAAI Conference on Artificial Intelligence*, 30(1). [check]
- [MOPIT (2023): add the source of the vehicle mix.]

---

## Appendix A: where each result lives
| Result | Folder or file |
|---|---|
| Per-agent table and figure | `docs/results_final.md`, `figures/report/final_results.png` |
| Regime map | `results_compare_grid`, `figures/report/regime_map.png` |
| Benchmark: specialists on cars | `results_compare_dqfd_tidal`, `results_compare_dqfd_rush`, `results_compare_dqh_r2`, `_r4`, `_r8` |
| Benchmark: Kathmandu-style | `results_compare_dqk_tidal`, `_rush`, `_peak`, `results_compare_kt`, `results_compare_kt_calib` |
| Generalist | `results_sweep_vg`, `results_compare_general` |
| Training sweeps | `results_sweep_v_*`, `results_sweep_vs_*`, `results_sweep_vt_*`, `results_sweep_vd_*`, `results_sweep_vk_*`, `results_sweep_vh_*` |
| Baseline tuning | `results_tune_actuated` |
| Early comparison (first fair test) | `results_compare_v1` |
| Final agents and manifest | `models/` |
| Detailed experiment log | `logs/week-06.md` |
