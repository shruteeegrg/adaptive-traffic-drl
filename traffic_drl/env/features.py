"""State and reward design for the full intersection (Week 4).

Pure functions over plain numbers -- no SUMO/TraCI here -- so the design
is unit-testable without a simulator and driven entirely by the `state:`
and `reward:` sections of the config. `TraciEnv` just feeds raw
measurements in.

State features (choose/order in `state.features`):
  queue         halting vehicles per approach            (n_approaches)
  waiting_time  summed waiting time per approach, seconds (n_approaches)
  phase         one-hot of the currently active green     (n_actions)
  phase_elapsed seconds since the last phase switch       (1)
Each group is divided by its scale so values sit near [0, 1], which
keeps neural-net training stable.

Reward is charged per SIMULATED SECOND, not per agent decision. Every
second the env accrues  queue_weight * halted + wait_weight * waiting time
+ backlog_weight * vehicles waiting to enter  (accrue_cost), and a
decision's reward is  -(accrued cost + switch_penalty if it switched) /
reward_scale.  Charging per decision instead is exploitable: a phase switch
burns 3 s of yellow inside one decision, so flipping every step makes
congestion go uncharged (the Week 6 sweep's degenerate "always flip" policy).
With the defaults (queue only, 1 s decisions) this equals the Week 2
reward, -sum(queue).
"""

import numpy as np

DEFAULT_STATE = {
    "features": ["queue"],
    "queue_scale": 1.0,
    "wait_scale": 1.0,
    "phase_elapsed_scale": 1.0,
}
DEFAULT_REWARD = {
    "queue_weight": 1.0,
    "wait_weight": 0.0,
    "backlog_weight": 0.0,
    "switch_penalty": 0.0,
    "reward_scale": 1.0,
}
KNOWN_FEATURES = ("queue", "waiting_time", "phase", "phase_elapsed")


def state_config(config: dict) -> dict:
    cfg = {**DEFAULT_STATE, **config.get("state", {})}
    unknown = set(cfg["features"]) - set(KNOWN_FEATURES)
    if unknown:
        raise ValueError(f"unknown state features {sorted(unknown)}; choose from {KNOWN_FEATURES}")
    return cfg


def reward_config(config: dict) -> dict:
    return {**DEFAULT_REWARD, **config.get("reward", {})}


def state_size(cfg: dict, n_approaches: int, n_actions: int) -> int:
    sizes = {"queue": n_approaches, "waiting_time": n_approaches,
             "phase": n_actions, "phase_elapsed": 1}
    return sum(sizes[f] for f in cfg["features"])


def build_state(cfg: dict, queues, waits, action: int, phase_elapsed: float, n_actions: int) -> np.ndarray:
    parts = []
    for f in cfg["features"]:
        if f == "queue":
            parts.append(np.asarray(queues, dtype=np.float32) / cfg["queue_scale"])
        elif f == "waiting_time":
            parts.append(np.asarray(waits, dtype=np.float32) / cfg["wait_scale"])
        elif f == "phase":
            one_hot = np.zeros(n_actions, dtype=np.float32)
            one_hot[action] = 1.0
            parts.append(one_hot)
        elif f == "phase_elapsed":
            parts.append(np.array([phase_elapsed / cfg["phase_elapsed_scale"]], dtype=np.float32))
    return np.concatenate(parts).astype(np.float32)


def accrue_cost(cfg: dict, queue_total: float, wait_total: float, backlog_total: float) -> float:
    """Cost per simulated second from instantaneous totals across approaches."""
    return (cfg["queue_weight"] * queue_total
            + cfg["wait_weight"] * wait_total
            + cfg["backlog_weight"] * backlog_total)


def compute_reward(cfg: dict, accrued_cost: float, switched: bool) -> float:
    """Reward for one decision, given the cost accrued over all the
    simulated seconds it spanned (yellow included)."""
    return -(accrued_cost + cfg["switch_penalty"] * (1.0 if switched else 0.0)) / cfg["reward_scale"]
