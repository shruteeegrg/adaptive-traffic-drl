# System Architecture

This diagram shows the layered architecture of the `traffic_drl` product: a
strict dependency chain where each layer only depends on the layer directly
beneath it. This is what makes the environment swappable (different
intersections via config) and the agent swappable (Q-table now, DQN later)
without touching the layers around them.

```mermaid
flowchart TB
    subgraph sim["Simulation layer"]
        SUMO["SUMO process<br/>(intersection.net.xml, .rou.xml)"]
    end

    subgraph cfg["Config layer"]
        YAML["intersection.yaml + scenario configs<br/>(traffic_drl/config.py)"]
    end

    subgraph env["Environment layer"]
        TraCI["TraciEnv<br/>(traffic_drl/env/traci_env.py)<br/>reset() / step(action)<br/>+ yellow-clearance safety logic"]
    end

    subgraph decision["Decision layer"]
        QTable["Q-table agent<br/>(traffic_drl/agent/q_table_agent.py)"]
        DQN["DQN agent<br/>(traffic_drl/agent/dqn_agent.py)"]
        Fixed["Fixed-time baseline<br/>(traffic_drl/baseline/)"]
    end

    subgraph orch["Orchestration layer"]
        CLI["traffic-drl CLI<br/>(traffic_drl/cli.py)<br/>train / evaluate / compare / demo"]
    end

    subgraph present["Presentation layer"]
        Viz["Shared plotting<br/>(traffic_drl/viz/)"]
        App["Streamlit demo app<br/>(traffic_drl/app.py)"]
    end

    subgraph artifacts["Artifacts (produced, not code)"]
        Checkpoints["checkpoints/"]
        Logs["logs/"]
        Docs["docs/ (report)"]
    end

    SUMO -->|TraCI socket| TraCI
    YAML -.->|resolves paths, ids, phases| TraCI
    TraCI --> QTable
    TraCI --> DQN
    TraCI --> Fixed
    QTable --> CLI
    DQN --> CLI
    Fixed --> CLI
    CLI --> Viz
    CLI --> Checkpoints
    CLI --> Logs
    Viz --> App
    Checkpoints --> App
    QTable -.-> App
    DQN -.-> App
    Fixed -.-> App
```

## Layer summary

- **Simulation layer** — SUMO owns the actual traffic physics as a separate
  headless process. Nothing in the Python code simulates traffic itself.
- **Config layer** — `intersection.yaml` and the scenario configs are what
  make the environment config-driven: file paths, traffic-light id, phase
  indices, and approaches all live here, not hardcoded in Python.
- **Environment layer** — `TraciEnv` is the *only* thing that talks to SUMO
  directly (via TraCI). It exposes a standard `reset()`/`step(action)`
  contract so every layer above it never needs to know SUMO exists. The
  yellow-clearance safety rule (no direct green-to-green switch) lives here,
  since it's a property of the environment's transition, not something each
  agent has to remember.
- **Decision layer** — the Q-table agent, DQN agent, and fixed-time baseline
  all consume the same environment contract, so they're interchangeable from
  the orchestration layer's point of view. This is what makes
  `traffic-drl compare` an apples-to-apples comparison.
- **Orchestration layer** — the CLI is the only layer that "knows about
  everything": it wires config + environment + agent/baseline together for a
  given command (`train`, `evaluate`, `compare`, `demo`).
- **Presentation layer** — `viz/` is shared plotting code consumed by both
  the CLI's saved report figures and the live Streamlit app, so there's one
  implementation of "plot the reward curve," not two.
- **Artifacts** — checkpoints, logs, and report docs are what training and
  evaluation *produce*; they sit outside the package itself.
