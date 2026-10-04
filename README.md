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
`DELIVERABLES.md` for the full breakdown — the product is deliverable #0,
with the contextual report, dashboard, and final report as supporting
evidence and documentation of it.

See `Project_Proposal.pdf` (Part 1) for the full abstract, objectives, and
risk analysis.

## Quickstart (once built out — see plan below)

```bash
pip install -e .
traffic-drl train --agent dqn --config configs/intersection.yaml
traffic-drl compare --config configs/intersection.yaml --scenarios rush_hour,low_traffic
traffic-drl demo   # launches the interactive Streamlit app
```

## Repository structure

```
traffic_drl/         installable package
  cli.py              CLI entry point (train / evaluate / compare / demo)
  env/                config-driven SUMO/TraCI environment wrapper
  agent/              Q-table baseline + hand-written MLP + DQN agent (done)
  baseline/           fixed-time controller for comparison
  viz/                shared plotting (reward, wait time, throughput)
  app.py              interactive Streamlit demo app
configs/              SUMO network/route files, hyperparameter + scenario configs
  scenarios/          rush_hour.yaml, low_traffic.yaml, ...
checkpoints/          trained model artifacts (gitignored, except a final shipped checkpoint)
logs/                 weekly logs (what was done / plan for next week) — one file per week
docs/                 contextual report, final report, comparative analysis
tests/                unit tests (agent, environment wrapper)
pyproject.toml        makes the repo `pip install -e`-able, defines the `traffic-drl` CLI
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

See `WORKFLOW.md` for full branch/PR conventions.

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

Requires SUMO installed separately — see https://sumo.dlr.de/docs/Installing/index.html
and the `SUMO_HOME` environment variable set for TraCI to work.

Sanity-check the environment (Week 2 onward):

```bash
traffic-drl env-check --config configs/intersection.yaml
```

## Status

Progress checklist (tick off as PRs merge):

- [x] Week 1 — Repo, environment & package setup
- [x] Week 2 — SUMO network + config schema
- [x] Week 3 — Baseline Q-table agent (verified on toy queue model; SUMO run pending)
- [x] Week 4 — State/reward design + NN architecture (tested with a fake traci; SUMO run pending)
- [x] Week 5 — DQN training loop (verified on toy queue model; SUMO run pending)
- [~] Week 6 — Training & convergence debugging (tooling done; real-SUMO sweep pending)
- [ ] Week 7 — Visualization module
- [ ] Week 8 — Fixed-timer baseline + scenarios + demo app v1
- [ ] Week 9 — Comparative analysis + app polish
- [ ] Week 10 — Final report + product polish
