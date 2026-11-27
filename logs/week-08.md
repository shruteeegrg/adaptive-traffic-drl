# Week 08 Log — Client product, Signal Studio and generalist agent v2

**Date submitted:** 2026-11-27
**Branch / PR:** `code-review-fixes` — https://github.com/shruteeegrg/adaptive-traffic-drl/pull/3

## Accomplished last week

- Started quality assurance as the supervisor advised: reviewed the code, fixed the issues found, and grew the automated tests to 201, all passing.
- Turned the project into a client product. A client enters their junction's traffic (vehicles per hour on each road, vehicle types, turns). The system compares the fixed timer, the density rule and the DQN, then gives a recommendation with a confidence label and a downloadable report. The DQN is only recommended if it significantly beats the rule.
- Built "Signal Studio", a web app with four steps: build traffic, live side-by-side comparison, verdict and report, and train your own agent. Checked it in a real browser and fixed the bugs found.
- Problem: the Week 7 single model failed on unseen traffic because it was trained on cars-only, straight-only traffic. I retrained it on 30 client-style patterns. On 17 held-out scenarios it is never significantly worse than the rule, better in 6, and 12% lower waiting on average.
- Reorganised the project folders and rewrote the reflective report.

## Planned for this week

- Re-tune the rule on mixed traffic and repeat the comparison.
- Update the final report with the product work.
- Continue quality assurance and prepare for the demo.

## Blockers / risks

- Results depend on the training seed (only 3 of 8 runs matched the rule).
- The rule was tuned on cars-only traffic, so part of the agent's lead may come from a mis-tuned rule.
- The junction layout is still fixed (one lane per road, two phases).

## Commits this period

- `1077e64` — fix: opt-in bootstrap through time-limit endings, reuse cached edge reads, document fixed phase layout
- `a773453` — feat: junction intake turns a client demand spec into a runnable scenario
- `6c595aa` — feat: advisor recommends fixed, density rule or learned controller with evidence and settings
- `ba76362` — feat: client report (self-contained HTML)
- `f13a1f2` — feat: playground in the app (own traffic, live comparison, report)
- `83f3aab` — feat: training jobs, train a DQN on a client's traffic in the background
- `04177d7` — feat: Signal Studio, the client web app (`traffic-drl serve`)
- `3288f96` — feat: generalist agent v2 trained on client-style traffic
- `fb06e4b` — chore: standard layout, results grouped under `results/`
