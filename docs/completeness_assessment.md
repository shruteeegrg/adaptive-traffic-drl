# Project completeness against the contextual report

Basis: `Contextual_Report_Shruti_Gurung-finale (2).pdf` (submitted 24 April 2026), the repository at commit `652aef0`, and the fresh-seed results in `figures/` (10 episodes, seeds 30000).

**Short verdict.** The engineering is ahead of what the report promised (hand-written NumPy network instead of PyTorch, resumable sweeps, tests, a live demo). The *evidence* is behind what the report promised in four places: statistical testing, number of evaluation episodes, heterogeneous (motorcycle) traffic, and the rush-hour success criterion. The last one is a result, not a bug: on rush hour the DQN ties the fixed timer.

Status key: **Done**, **Partly**, **Not done**, **Changed on purpose** (deviation I can justify).

## 1. Objectives (report section 1.4)

| # | Promise | Status | Evidence / gap |
|---|---|---|---|
| O1 | Four-lane urban intersection in SUMO, cars and **motorcycles**, Rush Hour and Low Traffic scenarios | **Partly** | Four-arm junction, **one lane per approach**, **cars only** (one `car` vType in every route file). Rush hour and low traffic exist, plus tidal. No motorcycles, buses or trucks. |
| O2 | DQN network model **in PyTorch** | **Changed on purpose** | Hand-written NumPy MLP with backpropagation, gradient-checked. Stronger fit to "from scratch"; must be stated in the thesis as a deliberate change. |
| O3 | Full training framework from scratch: epsilon-greedy, experience replay, Bellman targets | **Done** | `traffic_drl/agent/` (replay buffer, target network, Huber loss, Adam), 80+ tests. |
| O4 | Train **at least 500 episodes**; evaluate both controllers on **100 episodes** per scenario; **significance at alpha = 0.05** | **Partly** | Training runs used 80 to 250 episodes (best checkpoints often at episode 20 to 120). Final tests use **10** episodes. **No t-test or p-value anywhere in the code.** |
| O5 | Dashboard with accumulated reward per episode and average waiting time | **Partly** | `traffic-drl plot training` draws reward and waiting curves (static PNG); the Streamlit demo has a live waiting chart. No live training dashboard. |

## 2. Functional requirements (Table 5)

| ID | Requirement | Status | Note |
|---|---|---|---|
| FR1 | Four-arm intersection with Rush Hour and Low Traffic | **Done** (heterogeneity missing, see O1) | |
| FR2 | Per-lane vehicle counts and cumulative waiting time via TraCI | **Done** | Per-**approach-edge** (one lane each), so equivalent here. |
| FR3 | DQN selects a signal phase action **(0 to 3)** | **Changed** | Two actions (north-south green or east-west green); yellow is inserted by the environment. No left-turn phases because there are no turns. |
| FR4 | Reward = negative sum of waiting times per step | **Changed on purpose** | Cost per simulated second (queue + 0.1 x backlog) plus switch penalty. The original per-decision form let the agent cheat by flipping the light (found and fixed). |
| FR5 | Fixed-time baseline on identical simulation | **Done** | `traffic-drl baseline`, same seeds. |
| FR6 | Live Matplotlib dashboard of reward and waiting per episode | **Partly** | See O5. |
| FR7 | Scenario selectable by a single parameter | **Done** | `--scenario`. |

## 3. Non-functional requirements (Table 6)

| ID | Requirement | Status | Note |
|---|---|---|---|
| NFR1 | Training in under 6 hours on an i5, 8 GB, no GPU | **Done** | A 120-episode run takes minutes to under 10 minutes. Record the exact figure in the thesis. |
| NFR2 | Distinct, logged seeds | **Done** | Per-episode seeds; train, selection and test seeds separated. |
| NFR3 | No high-level RL libraries | **Done** | NumPy only. |
| NFR4 | Modular, documented, README with run procedure | **Partly** | Modular and tested; the README still lists weeks 7 to 10 as unticked and needs a proper "how to run" section (a fresh-clone check is still outstanding). |
| NFR5 | Dashboard updates during training | **Not done** (Could priority) | |

## 4. Testing and evaluation strategy (sections 6.1, 6.2)

| Promise | Status | Note |
|---|---|---|
| Unit tests: replay buffer FIFO and sampling, Bellman target, epsilon schedule | **Done** | `tests/test_dqn.py`, `tests/test_nn.py`. |
| Integration test of the TraCI bridge | **Done** | `tests/test_env_smoke.py` (needs SUMO, passes on Windows). |
| System test: reward trend and loss stabilisation | **Partly** | Shown by curves and a toy convergence test; no automated assertion on the real simulator. |
| 100 trials per scenario, **two-sample t-test**, alpha = 0.05; main metric average wait per car | **Not done** | 10 trials, no test. Main metric used is vehicles waiting (queue + backlog); `avg_wait_per_vehicle` is also recorded. |
| Success = significantly lower waiting than fixed-time, **especially on Rush Hour** | **Not met on Rush Hour** | See section 5. |
| Generalisation: **trained on Rush Hour only, tested on Low Traffic** | **Not tested in that direction** | We tested tidal-only to rush and low traffic (it failed). Rush-trained to low traffic is a one-command test. |

## 5. What the data says today (10 episodes, Welch t-test computed offline from `figures/*.csv`)

| Scenario | Fixed timer | DQN | t | Reading |
|---|---|---|---|---|
| Tidal | 115.0 | 9.9 | 79 | Overwhelmingly significant. |
| Rush hour | 139.7 | 140.8 | -0.35 (p about 0.7) | **No difference.** Objective O4 / success criterion not met. |
| Low traffic | 1.5 | 0.5 | 143 | Statistically significant, practically negligible (both near zero); the DQN switches 3x more often. |

Two points to prepare for the viva:
- With 100 episodes, even a 1 to 2 percent gap becomes "significant". The thesis should fix a **practical-significance threshold in advance** (for example at least 5 percent, tied to survey question 9's "minimum improvement") and report effect sizes and confidence intervals as well as p-values.
- A tie on saturated, symmetric traffic is a legitimate finding (a fixed timer is already near-optimal there). It must be reported as such, with the evidence of the experiments that tried to beat it.

## 6. Deviations the thesis must explain (design decisions vs the report)

| Report said | Built | Justification available |
|---|---|---|
| PyTorch 2.x | NumPy MLP | Meets NFR3 literally; no GPU needed. |
| Two hidden layers of 128, ReLU, buffer 50,000, epsilon to 0.01, lr 1e-3, gamma 0.99 | 64 and 64, buffer 20,000, epsilon to 0.05, lr 5e-4 to 1e-3, gamma 0.95 then **0.99** | Sweeps; gamma 0.99 (the report's own risk-register value) turned out to be the key setting for rush hour. |
| 4 actions | 2 actions | No turning movements in scope. |
| Reward: sum of waiting times | Per-second queue plus backlog cost plus switch penalty | Reward exploit found and fixed; backlog needed because approach edges hold about 12 cars. |
| Kathmandu junction from OpenStreetMap (Kalanki or Koteshwor) | Synthetic four-arm junction generated with netconvert | Simplification; must be stated, or implemented (see plan). |
| Vehicle mix from MOPIT 2023 (motorcycles 60 to 65 percent, cars about 20, buses about 8) | Cars only | **Unjustified so far.** This is the stated contribution of the project (heterogeneous South Asian traffic), so it is the largest gap. |
| Double DQN cited (Gu, 2020) as a fix for divergence | Plain DQN with a target network | Not implemented; cheap to add and to compare. |
| Only fixed-time baseline in the evaluation | Same | Actuated controller was discussed in the review but never benchmarked. |

## 7. Problems inside the contextual report itself (fix in the thesis)

1. **Survey figures.** Section 3.5 says the graphs "show the *expected* distribution of responses ... using data gathered during pilot testing" and "projected distribution", while section 3.3.1 says 43 real responses. The charts must come from the real response sheet, and the text must say so. Also the **Appendix A form differs from Table 2** (for example question 4 has no "Always" option in the form; the form shows different options for the congestion-cause and AI-comfort questions). Reconcile the instrument, the table and the charts before the thesis.
2. **Question 9 asks for minutes of commute saved**, but the system measures vehicles waiting at one junction (seconds per vehicle). The thesis needs an explicit, honest conversion or a statement that the survey threshold cannot be mapped to a single junction.
3. **Citation check.** Rasheed et al. (2020) appears as pp. 208032 to 208051 in the proposal and pp. 208016 to 208044 in the report; the in-text form "(F. Rasheed, 2020)" is also malformed. Verify each reference against the DOI and use one style.
4. **Claims stronger than the evidence.** "consistently and statistically significantly outperform" is stated from the cited studies; the thesis should say what *our* experiments found, including the tie on rush hour.

## 8. The supervisor's feedback on the literature review

Feedback: *lacks critical synthesis, mostly descriptive summaries.* The fix is structural, not more reading:

1. **Organise by questions, not by paper.** For each theme (reward design, state representation, algorithm stability, simulator choice, evaluation protocol) state what the papers *agree* on, where they *disagree*, and what is *untested*.
2. **Build a comparison matrix** (one row per paper): algorithm, state, action space, reward, scenario and traffic mix, baseline used, number of test runs, statistics reported, sim-to-real evidence. Gaps become visible (for example how many compare against an actuated baseline, how many report significance, how many use heterogeneous traffic).
3. **Set sources against each other.** Examples already in the report: plain DQN divergence (Gu, 2020) against the reported stability of DQN; single-objective waiting-time reward (Genders, 2016; Koohy, 2022) against multi-objective shaping (Hendra, 2023).
4. **Close the loop with your own results.** This project produced findings that bear directly on the literature: a per-decision reward let the agent cheat; a mean-queue metric hid congestion on short approach roads; best-of-many selection overstated performance; discount factor 0.99 versus 0.95 changed rush-hour results; a policy trained on one demand pattern did not transfer. A good synthesis says which published claims these support or qualify.
5. **State the gap precisely** and show that the project fills it (heterogeneous traffic, from-scratch implementation, honest negative results).

(Source papers have not been re-read for this assessment; the notes above rely on how the contextual report describes them. Verify each against the paper before reuse.)

## 9. Prioritised plan for the extra week

Priority 1 closes the gaps between promise and evidence; priority 2 strengthens the science; priority 3 is delivery.

| Day | Work | Where |
|---|---|---|
| 1 | `traffic-drl compare`: runs fixed timer and a checkpoint on N episodes (default 100) for chosen scenarios, prints means, 95 percent CI, Welch t-test p-value, effect size, and a practical-significance flag (default 5 percent). Replaces the stub. | Mac (code, tests) |
| 1 to 2 | Heterogeneous fleet: route generator option with a MOPIT-based vehicle mix (motorcycle, car, bus, other) and scenario variants; baseline on them. | Mac, then Windows |
| 2 | Double DQN as an option, with a test; run DQN vs Double DQN on rush hour, 4 seeds each. | Mac, Windows (about 1.5 h) |
| 2 | Generalisation test promised in the report: rush-trained model on low traffic and tidal. | Windows (minutes) |
| 2 to 4 | Final training runs: 500 episodes on the heterogeneous scenarios with the best settings (gamma 0.99, penalty 5), best-checkpoint selection every 10 episodes; log the reward curve. | Windows (about 3 h unattended) |
| 3 | Actuated baseline (queue-responsive heuristic) as a second, stronger comparison. | Mac, Windows |
| 4 | Training-curves tab in the demo app (reward and waiting per episode, from the saved CSVs) for FR6 and NFR5. | Mac |
| 5 | Final 100-episode comparison on fresh seeds, all scenarios, with statistics; regenerate figures and the demo results tab. | Windows |
| 6 | Docs: README (how to run, fresh-clone check), requirements traceability table, thesis outline updates, literature synthesis matrix, errata list for section 7. | Mac |
| 7 | Full test run on Windows, demo rehearsal, backup recording, tag `v1.0`. | Windows |

**Decision rule, set now so results cannot move it:** rush hour counts as "improved" only if the DQN is below the fixed timer by at least 5 percent *and* Welch p < 0.05 on 100 fresh-seed episodes. Otherwise it is reported as a tie, with the experiments listed.

**Risks:** heterogeneous traffic changes queue lengths and may need re-tuning; longer training has made results worse so far (best checkpoints at episodes 20 to 120), so the 500-episode objective is run with best-checkpoint selection and the drift is reported; the rush-hour result may stay a tie.
