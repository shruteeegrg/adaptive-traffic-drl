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

Reward: -(queue_weight * total queue + wait_weight * total waiting time)
        - switch_penalty * (1 if the phase switched this step)
divided by `reward_scale`. With the defaults (queue only, no penalty,
scale 1) this equals the Week 2 reward, -sum(queue).
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


def compute_reward(cfg: dict, queues, waits, switched: bool) -> float:
    cost = (cfg["queue_weight"] * float(np.sum(queues))
            + cfg["wait_weight"] * float(np.sum(waits))
            + cfg["switch_penalty"] * (1.0 if switched else 0.0))
    return -cost / cfg["reward_scale"]
