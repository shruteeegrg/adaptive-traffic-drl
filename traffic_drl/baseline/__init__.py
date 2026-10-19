# Reference controllers the learned agents are measured against.
#   FixedTimeAgent       constant green per direction (a plain timer)
#   DensityActuatedAgent gives green to the heavier approach, like detector-based
#                        adaptive signals (e.g. Lalitpur's, 2024)
from traffic_drl.baseline.actuated import DensityActuatedAgent
from traffic_drl.baseline.fixed_time import FixedTimeAgent

__all__ = ["FixedTimeAgent", "DensityActuatedAgent"]
