# Weekly updates after Week 5

Same format as the Week 5 update. Week 6 covers 12 to 20 Oct; Week 7 covers 21 to 29 Oct. The detailed record with every number is in `logs/week-06.md`.

---

## Week 6

**Summary of progress (including any problems)**

- Compared the project against the contextual report. The main gaps were results from only 10 test runs, no significance tests, and a fixed timer as the only baseline.
- Built `traffic-drl compare`: identical traffic for every controller, 95% confidence intervals and significance tests. A result counts as "better" only if it is statistically significant and at least 5% and 2 vehicles better.
- Built a stronger baseline modelled on Nepal's first AI-enabled lights (Lalitpur): a rule that gives green to the road with more vehicles. **Problem:** my first version counted only stopped vehicles and lost to the fixed timer. I fixed it to count all vehicles, like a real detector, and tuned it on separate seeds.
- First fair test (100 runs per scenario): the tuned rule beat the fixed timer everywhere. On tidal, waiting was 114.0 for fixed, 7.2 for the rule and 10.1 for the best DQN. On rush hour, the DQN only tied the fixed timer. So every earlier DQN was below the rule.
- DQN training was unstable (good early, then drifting worse). I gave it the same vehicle counts as the rule and added Double DQN, gradient clipping and learning-rate decay. Starting it from the rule's experience kept 2 of 4 runs good on tidal, but none reached the rule.
- Not solved: a DQN that matches the rule reliably, and one model for all scenarios.

**Plan for next week**

- Try learning from demonstrations: keep the rule's decisions in a memory that is never overwritten, and test on tidal and rush hour with 100 fresh runs.
- Add realistic Kathmandu traffic (motorcycles, buses, turns), retry one model for all patterns, and map where adaptive control helps.

---

## Week 7

**Summary of progress (including any problems)**

- Learning from demonstrations fixed the instability. In the 100-run test the DQN **matches the rule** (tidal 6.9 to 7.4 against 7.2, rush hour 122 to 127 against 126.6). Under our rule none counts as clearly better.
- Added Kathmandu-style traffic (motorcycles, buses, turns). The vehicle mix is an assumption I still need to confirm. **Problem:** my first demand levels overloaded the junction, because turning vehicles halve a single lane's capacity. I recalibrated, and the DQN now ties the rule on tidal and peak.
- One model trained on 12 random demand patterns does not match the rule on unseen traffic (a negative result). I kept the specialist models.
- Regime map: the rule beats the fixed timer in all 16 demand patterns tried, by 20 to 98%. In heavy, uneven traffic 3 of 12 DQN agents were significantly better than the rule (5 to 11%), 2 worse and 7 tied. So the benefit is real but depends on the training run.
- The demo now shows fixed, rule and DQN side by side on 9 scenarios. Clean-install checks on Windows and Mac found and fixed three problems. Tagged `v1.0`.
- Updated the slides and the reflective report to the final results, and wrote a first draft of the final report (method, results, evaluation and conclusions). The literature review is still only a skeleton.
- Not solved: a DQN that beats the rule reliably, and one model for every pattern.

**Plan for next week**

- Give the demo with a tested backup laptop and a screen recording.
- Rewrite the literature review with critical synthesis (my supervisor's feedback) and finish the final report (requirements, discussion, references).
- Check the sources I flagged (DQfD, Double DQN, the MOPIT vehicle-mix source) and fix the survey figures in the contextual report.
