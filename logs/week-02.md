# Week 2 Log — SUMO Network + Config Schema

**Date submitted:** YYYY-MM-DD
**Branch / PR:** `week-02-sumo-network`

## Accomplished last week (Week 1)

- Created the GitHub repository and pushed the initial commits; added the
  supervisor as a collaborator.
- Structured the project as an installable Python package (`pyproject.toml`)
  with a `traffic-drl` CLI skeleton.
- Finalised the project deliverables and the 10-week plan.
- Installed SUMO/TraCI and confirmed the environment.

## This week (Week 2)

- [x] Designed the YAML config schema for the intersection (`configs/intersection.yaml`):
  file paths, traffic-light id, phase indices, step/episode length, approaches.
- [x] Built the single 4-arm signalized intersection network from plain
  node/edge XML via `netconvert` (`scripts/generate_network.sh` ->
  `configs/intersection.net.xml`) -- one controlled junction (`A1`) with
  four boundary approach edges (east/north/west/south), no hand-edited XML.
- [x] Generated demand/route files for the base config and both stress-test
  scenarios via a single script (`scripts/generate_routes.py`):
  `configs/intersection.rou.xml` (300 veh/h/approach), plus
  `configs/scenarios/rush_hour.rou.xml` (900) and `low_traffic.rou.xml` (120).
- [x] Implemented the config-driven TraCI environment wrapper
  (`traffic_drl/env/traci_env.py`, class `TraciEnv`): `reset()`/`step(action)`,
  reading queue length per approach as state, with automatic yellow-phase
  clearance on a green-to-green switch (an agent can never request an
  unsafe direct switch).
- [x] Proved it actually works, not just "should work": `tests/test_env_smoke.py`
  and `traffic-drl env-check --config configs/intersection.yaml` both run a
  real headless SUMO simulation end to end, and were re-run twice to confirm
  the environment resets and produces identical results both times
  (repeatable, per the Simulation Environment "done when" criterion in
  DELIVERABLES.md).

## Planned for next week (Week 3)

- [ ] Implement the tabular Q-learning baseline agent
  (`traffic_drl/agent/q_table_agent.py`) on a simplified, discretized
  version of the state space (per the proposal's own risk mitigation --
  de-risk convergence before scaling to DQN).
- [ ] Wire `traffic-drl train --agent qtable --config ...` to actually run it.
- [ ] Log/plot the Q-table agent's reward curve to sanity-check it's learning
  anything before moving on to the neural-network agent.

## Blockers / risks

- None blocking. The environment step currently advances the simulation by
  a fixed `step_length` per action with a hardcoded 2-action space
  (NS-green / EW-green); this is deliberately minimal for Week 2 and will
  need revisiting once the Q-table/DQN agents define their actual state
  discretization in Week 3-4.

## Commits this period

-
