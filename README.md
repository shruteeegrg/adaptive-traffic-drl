# Adaptive Traffic Signal Control System using Deep Reinforcement Learning

Final Year Project (CIS013-3) — University of Bedfordshire
Student: Shruti Gurung (2337686) · Supervisor: Pawan KC

## Overview

This project builds a Deep Q-Network (DQN) agent, implemented from scratch
(no Stable-Baselines or other high-level RL libraries), to control traffic
signal phases at a simulated urban intersection in
[SUMO (Simulation of Urban Mobility)](https://sumo.dlr.de/docs/), and
compares its performance against a standard fixed-time controller.

See `Project_Proposal.pdf` (Part 1) for the full abstract, objectives, and
risk analysis, and `DELIVERABLES.md` for the finalized list of five
deliverables (contextual report, simulation environment, RL agent code,
performance dashboard, comparative analysis) mapped to concrete files and
"definition of done" criteria.

## Repository structure

```
src/
  env/       SUMO/TraCI environment wrapper — network, routes, state/reward extraction
  agent/     Q-table baseline + DQN agent (neural net, replay buffer, training loop)
  baseline/  Fixed-time traffic controller for comparison
  viz/       Dashboard / live plotting of reward, wait time, throughput
configs/     SUMO network/route files, hyperparameter configs
logs/        Weekly logs (what was done / plan for next week) — one file per week
docs/        Contextual report, final report, comparative analysis
tests/       Unit tests (agent, environment wrapper)
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
| 1 | Repo + environment setup | Repo live, collaborator added, Python env + SUMO/TraCI installed and pinned, first commit proving the env runs |
| 2 | SUMO network construction | Hand-built single-intersection `.net.xml`/`.rou.xml`, TraCI script reading queue length/occupancy and forcing phase changes |
| 3 | Baseline Q-table agent | Q-table RL agent on a simplified single-lane state space — de-risks convergence before scaling up |
| 4 | State/reward design + NN architecture | Full intersection state/action/reward design; hand-written neural net (PyTorch/TF) unit-tested on dummy data |
| 5 | DQN training loop | Replay buffer, target network, epsilon-greedy policy, backprop step — running end-to-end |
| 6 | Training & convergence debugging | Reward-curve tracking, hyperparameter sweeps, model checkpointing |
| 7 | Visualization module | Live dashboard: accumulated reward, average wait time, throughput |
| 8 | Fixed-timer baseline + stress tests | Baseline controller implemented; "rush hour" / "low traffic" scenarios run against both controllers |
| 9 | Comparative analysis | Aggregated metrics, statistical comparison, results section drafted |
| 10 | Final report + cleanup | Final report complete, code cleaned up, final PR merged |

## Setup

```bash
conda env create -f environment.yml
conda activate traffic-drl
# or: pip install -r requirements.txt
```

Requires SUMO installed separately — see https://sumo.dlr.de/docs/Installing/index.html
and the `SUMO_HOME` environment variable set for TraCI to work.

## Status

Progress checklist (tick off as PRs merge):

- [ ] Week 1 — Repo & environment setup
- [ ] Week 2 — SUMO network construction
- [ ] Week 3 — Baseline Q-table agent
- [ ] Week 4 — State/reward design + NN architecture
- [ ] Week 5 — DQN training loop
- [ ] Week 6 — Training & convergence debugging
- [ ] Week 7 — Visualization module
- [ ] Week 8 — Fixed-timer baseline + stress tests
- [ ] Week 9 — Comparative analysis
- [ ] Week 10 — Final report + cleanup
