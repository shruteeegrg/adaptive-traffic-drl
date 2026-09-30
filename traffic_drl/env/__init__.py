# Config-driven SUMO/TraCI environment wrapper, plus a SUMO-free toy
# model for fast agent checks. TraciEnv is imported lazily so the toy env
# and the agents work on machines without SUMO/traci set up.
from traffic_drl.env.toy_env import SimpleQueueEnv

__all__ = ["TraciEnv", "SimpleQueueEnv"]


def __getattr__(name):
    if name == "TraciEnv":
        from traffic_drl.env.traci_env import TraciEnv

        return TraciEnv
    raise AttributeError(name)
