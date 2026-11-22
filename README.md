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
- A **single model for every demand pattern** does not yet match the rule on unseen demand (negative result; specialists are kept).
- Plain DQN training was unstable and lost to the rule; the demonstrations are what made it reliable.

Limits: one junction, one lane per road, two phases (the phase layout is fixed in code, so a different junction layout needs `GREEN_PHASES` changed); the vehicle mix (62% motorcycles, 22% cars, 8% buses, 8% light goods)
is an assumption to be checked against its source; motorcycles queue in single file; the rule was tuned on cars-only traffic.

## Repository structure

```
traffic_drl/         installable package
  cli.py              CLI entry point (train / evaluate / compare / demo)
  env/                config-driven SUMO/TraCI environment wrapper
  agent/              Q-table baseline + hand-written MLP + DQN agent (done)
  baseline/           fixed-time controller and the density-responsive rule (the benchmark to beat)
  stats.py            Welch / paired t-tests, confidence intervals, effect size (no SciPy)
  compare.py          head-to-head comparison with statistics (`traffic-drl compare`)
  viz/                shared plotting (reward, wait time, throughput)
  app.py              interactive Streamlit demo app
configs/              SUMO network/route files, hyperparameter + scenario configs
  scenarios/          rush_hour, low_traffic, tidal, Kathmandu-style (*_kt), grid/ (regime map), pool/ (randomised demand)
models/               final trained agents (all seeds) and manifest.json (default per scenario, chosen on selection seeds)
scripts/              route generators, tuning, regime grid, results table and figure builders
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
