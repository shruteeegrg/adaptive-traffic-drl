# Deliverables

Finalized from the project proposal's "Project deliverables" section. Five
artifacts, each with a concrete location in this repo and a definition of
"done." Nothing here is a web app or UI — it's a simulation, an agent, and
the evidence that the agent works.

## 1. Contextual Report (Literature Review + Testing)

- **Where:** `docs/contextual_report.md` (or §1 of `docs/final_report.md`)
- **Content:** analysis of existing traffic control methods (fixed-time,
  actuated) and RL approaches (Q-learning, DQN), grounded in the sources
  already in the proposal (Sutton & Barto 2018; Mnih et al. 2015; Rasheed
  et al. 2020; Lopez et al. 2018).
- **Done when:** it justifies *why* DQN + SUMO over the alternatives, not
  just describes them.

## 2. Simulation Environment

- **Where:** `configs/intersection.net.xml`, `configs/routes.rou.xml`,
  `configs/*.sumocfg`, `src/env/` (TraCI wrapper).
- **Content:** a hand-built single-intersection SUMO network with realistic
  (or at least plausible) traffic demand, and a Python wrapper exposing
  `reset()` / `step(action)` returning per-lane queue length / occupancy as
  state.
- **Done when:** the environment runs headlessly and repeatably, and state
  extraction is verified against SUMO's own GUI/output for a few manual
  spot checks.

## 3. RL Agent Code

- **Where:** `src/agent/q_table_agent.py` (baseline), `src/agent/dqn_agent.py`
  (network + replay buffer + target network + training loop).
- **Constraint:** implemented from scratch — no Stable-Baselines or
  equivalent high-level RL library, per the proposal.
- **Done when:** the Q-table baseline converges on the simplified
  single-lane problem, and the DQN agent trains to a stable (not
  necessarily optimal) policy on the full intersection, with a saved
  checkpoint (`checkpoints/dqn_final.pt`) and a logged reward curve.

## 4. Performance Dashboard

- **Where:** `src/viz/dashboard.py`.
- **Content:** plots of accumulated reward, average wait time, and
  throughput, over training and over evaluation runs.
- **Done when:** it can render from a saved log file (not just live during
  training), so results are reproducible without rerunning training.

## 5. Comparative Analysis (Final Report)

- **Where:** `docs/final_report.md` (results + discussion sections).
- **Content:** DQN agent vs. fixed-time controller, compared on average
  wait time and throughput, across at least two scenarios ("rush hour",
  "low traffic"), with the comparison stated in aggregate statistics
  (mean/variance across runs), not a single anecdotal run.
- **Done when:** the comparison is quantified and discussed, including
  where the DQN agent does *not* beat the baseline, if that happens —
  a negative or mixed result, honestly reported, is a valid finding.

## Explicitly not deliverables

- No web frontend, no user-facing app — the "interface" is the SUMO GUI
  (for demos) and the dashboard plots (for results).
- No deployment/production concerns — this is a research simulation, not a
  service.
