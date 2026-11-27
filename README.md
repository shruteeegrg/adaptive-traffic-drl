# Adaptive Traffic Signal Control System using Deep Reinforcement Learning

Final Year Project (CIS013-3) — University of Bedfordshire
Student: Shruti Gurung (2337686) · Supervisor: Pawan KC

## Overview

This project builds a Deep Q-Network (DQN) agent, implemented from scratch
(no Stable-Baselines or other high-level RL libraries), to control traffic
signal phases at a simulated urban intersection in
[SUMO (Simulation of Urban Mobility)](https://sumo.dlr.de/docs/), and
compares its performance against a standard fixed-time controller.

**The deliverable is a product, not a script:** `traffic_drl` is an
installable, config-driven Python package with a CLI (`traffic-drl`) and
an interactive demo app, not code hardcoded to one intersection file. See
`docs/project/DELIVERABLES.md` for the full breakdown — the product is deliverable #0,
with the contextual report, dashboard, and final report as supporting
evidence and documentation of it.

See `docs/project/Project_Proposal.pdf` (Part 1) for the full abstract, objectives, and
risk analysis.

## Quickstart

```bash
pip install -e ".[sumo]"               # the [sumo] extra installs the SUMO simulator itself (eclipse-sumo)
traffic-drl serve                      # Signal Studio, the client web app: build traffic, compare live, get a verdict and report, train an agent (needs SUMO)
traffic-drl demo                       # the earlier Streamlit demo: fixed timer vs density rule vs DQN, side by side (needs SUMO)
traffic-drl compare --config configs/dqn_v_dqfd.yaml --scenarios tidal,rush_hour \
    --controller fixed --controller "rule=actuated:min=10,max=40,ratio=4,gap=0" \
    --controller dqn=dqn:models/dqfd_rush_s2.npz@configs/dqn_v_dqfd.yaml \
    --reference rule --episodes 100 --seed-base 30000
```

`compare` prints the mean waiting with a 95% confidence interval, Welch and paired t-tests, Cohen's d and a verdict
that needs both statistical and practical significance. Train an agent with `traffic-drl train` or run a seed sweep with
`traffic-drl sweep` (see `configs/` for the recipes).

## Results at a glance

The question: *when is a learned signal controller worth it against a simple, well-tuned rule?* All numbers are 100
episodes on seeds nobody trained or tuned on; the full table with every trained agent is `docs/results_final.md`.

- A **density rule** (count vehicles, give green to the busier road, as Lalitpur's 2024 lights do) beats a fixed timer in all
  16 cells of a demand-by-unevenness grid, by 20 to 98% (`figures/report/regime_map.png`).
- A **DQN trained from the rule's demonstrations** (frozen demonstration buffer plus a margin loss) matches the rule, and in
  heavy, uneven or near-capacity traffic some agents are 5 to 14% better. This is seed-dependent: other agents tie or are a few percent worse.
- A **single model for every demand pattern**: trained on cars-only traffic it did not match the rule on unseen demand (negative result). Retrained on client-style traffic (mixed vehicles, turning, quiet to near capacity) the generalist v2 is never significantly worse than the rule on 17 held-out scenarios and better in 6, with caveats on seed luck and on a rule tuned for cars only (`docs/results_generalist_v2.md`).
- Plain DQN training was unstable and lost to the rule; the demonstrations are what made it reliable.

Limits: one junction, one lane per road, two phases (the phase layout is fixed in code, so a different junction layout needs `GREEN_PHASES` changed); the vehicle mix (62% motorcycles, 22% cars, 8% buses, 8% light goods)
is an assumption to be checked against its source; motorcycles queue in single file; the rule was tuned on cars-only traffic.

## Repository structure

```
traffic_drl/          installable package
  cli.py               CLI entry point (train / sweep / compare / intake / advise / report / train-job / serve / demo)
  env/                 config-driven SUMO/TraCI environment wrapper
  agent/               Q-table baseline + hand-written MLP + DQN agent
  baseline/            fixed-time controller and the density rule (the benchmark to beat)
  intake.py advisor.py report.py training_job.py pool.py   the product pipeline: client traffic -> verdict -> report -> own agent
  web/                 Signal Studio, the FastAPI web app (server.py + static front end)
  app.py demo_core.py  the earlier Streamlit demo
  stats.py compare.py sweep.py viz/   statistics, head-to-head comparison, seed sweeps, plots
configs/               SUMO network/route files, recipes (dqn_*.yaml), scenarios/ (rush_hour, tidal, grid/, pool/, client_pool/)
models/                shipped trained agents and manifest.json (gen_v2.npz is the default generalist)
checkpoints/           the few committed checkpoints the demo needs (the rest is gitignored)
scripts/               pool generators, tuning, generalist training/exam, results table and figure builders
results/               raw experiment outputs, see results/README.md
  comparisons/ sweeps/ training/ tuning/
figures/               figures used in the report (report/) and early training curves
docs/                  reports, result tables, architecture, project/ (proposal, deliverables, workflow)
logs/                  weekly logs, one file per week
tests/                 unit and integration tests
projects/  runs/       local working folders (client jobs, training runs); gitignored
pyproject.toml         makes the repo `pip install -e`-able, defines the `traffic-drl` CLI
```

## Workflow

- `main` is protected. All work happens on a weekly feature branch
  (`week-01-env-setup`, `week-02-sumo-network`, ...) merged via a Pull
  Request.
- Each PR description doubles as that week's log entry (mirrored into
  `logs/week-XX.md`): what was accomplished the previous week, what's
  planned for the current week.
- Commits should land through the week as work happens, not as a single
  end-of-week dump — the commit history is what backs up the weekly log.
- The weekly log is only considered valid if the corresponding work is
  reflected in commits/PRs in this repo.

See `docs/project/WORKFLOW.md` for full branch/PR conventions.

## 10-week plan

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Repo + environment + package setup | Repo live, collaborator added, Python env + SUMO/TraCI installed and pinned, `pyproject.toml` + CLI skeleton (`traffic-drl` runs with stub subcommands) |
| 2 | SUMO network + config schema | Hand-built single-intersection `.net.xml`/`.rou.xml`, YAML config schema for intersection layout, config-driven TraCI env wrapper (no hardcoded paths) |
| 3 | Baseline Q-table agent | Q-table RL agent on a simplified single-lane state space, wired into `traffic-drl train --agent qtable` |
| 4 | State/reward design + NN architecture | Full intersection state/action/reward design (config-driven hyperparams); hand-written neural net unit-tested on dummy data |
| 5 | DQN training loop | Replay buffer, target network, epsilon-greedy policy, backprop step, wired into `traffic-drl train --agent dqn` |
| 6 | Training & convergence debugging | Reward-curve tracking, hyperparameter sweeps, model checkpointing (`checkpoints/dqn_final.npz`) |
| 7 | Visualization module | `traffic_drl/viz` — plots from saved logs, wired into `traffic-drl evaluate` |
| 8 | Fixed-timer baseline + scenarios + demo app v1 | Baseline controller + `rush_hour`/`low_traffic` scenario configs; `traffic-drl compare` working; first working version of the Streamlit demo app |
| 9 | Comparative analysis + app polish | Aggregated metrics via `traffic-drl compare`, statistical comparison, results section drafted; side-by-side view in the demo app |
| 10 | Final report + product polish | Final report complete; fresh-clone `pip install -e .` + `traffic-drl demo` verified working end-to-end; final PR merged |

## Setup

```bash
conda env create -f environment.yml
conda activate traffic-drl
pip install -e .
```

Running simulations (training, `compare`, the live demo) needs the SUMO simulator. The easiest way is the PyPI package:
`pip install -e ".[sumo]"` (or `pip install eclipse-sumo` into the active environment). Alternatively install SUMO from
https://sumo.dlr.de/docs/Installing/index.html and set `SUMO_HOME`. The tests, `scripts/build_results.py` and the
"Test results" tab of the demo do not need SUMO.

Sanity-check the environment (Week 2 onward):

```bash
traffic-drl env-check --config configs/intersection.yaml
```

## Status

All implementation, experiments and the results table are complete (`docs/results_final.md`). The weekly logs in `logs/` record
what was tried in order, including the dead ends. Remaining work is the written report and the demo.

Reproduce the headline numbers: `python scripts/build_results.py` rebuilds the table and figure from the saved
`results_compare_*` folders; `traffic-drl compare` (above) regenerates any single cell on a machine with SUMO.
