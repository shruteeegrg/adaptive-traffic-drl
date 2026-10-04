# Fixed-time traffic signal controller, the baseline the trained DQN agent is
# measured against. Week 6: FixedTimeAgent + `traffic-drl baseline`;
# Week 8 wires it into `traffic-drl compare` across scenarios.
from traffic_drl.baseline.fixed_time import FixedTimeAgent

__all__ = ["FixedTimeAgent"]
