"""Randomised client-style traffic, for training and testing one agent that must cope with whatever a client builds.

The earlier generalist was trained on a pool of cars-only, straight-only traffic with no light-demand cases, then
met motorcycle-heavy traffic with turns in the web app: a distribution shift, not a capacity limit. This pool draws
the same space a client can describe in the app (see traffic_drl.intake): per-road demand from quiet to near
capacity, balanced / uneven / flipping patterns, cars-only or mixed fleets, and turning shares. Every scenario is
30 minutes, the length of an evaluation episode.

Three disjoint draws keep the exam honest (different seeds, different names, never mixed):
  train   what the agent learns on
  select  what picks the best checkpoint and the best seed (selection seeds, 10000+ / 20000+)
  test    never used for any choice; compared on test seeds (30000+)
`PRESETS` are the five starting points of the web app with its default mix and turning, a test set a client would
actually recognise.
"""

import json
import math
import os
import random

from traffic_drl import intake

KINDS = ("balanced", "uneven", "flipping")
RATE_RANGE = (80.0, 1300.0)      # veh/h on the heavier axis, log-uniform: quiet to near capacity
DEFAULT_MIX = {"motorcycle": 0.62, "car": 0.22, "bus": 0.08, "goods": 0.08}
PRESETS = {
    "preset_balanced": ({"north": 500, "east": 500, "south": 500, "west": 500}, False),
    "preset_morning_rush": ({"north": 800, "east": 350, "south": 800, "west": 350}, False),
    "preset_tidal_swing": ({"north": 900, "east": 300, "south": 900, "west": 300}, True),
    "preset_near_capacity": ({"north": 850, "east": 850, "south": 850, "west": 850}, False),
    "preset_quiet": ({"north": 120, "east": 120, "south": 120, "west": 120}, False),
}


def _demand(rates: dict, swap: bool, minutes: float = 30.0):
    """A spec `demand` value: constant, or two periods with the NS and EW axes trading rates (a tidal swing)."""
    if not swap:
        return dict(rates)
    flipped = {"north": rates["east"], "east": rates["north"], "south": rates["west"], "west": rates["south"]}
    return [{"minutes": minutes / 2, **rates}, {"minutes": minutes / 2, **flipped}]


def _mix(rng: random.Random):
    if rng.random() < 0.3:
        return "cars"
    raw = {"motorcycle": rng.uniform(0.2, 0.7), "car": rng.uniform(0.1, 0.5),
           "bus": rng.uniform(0.02, 0.15), "goods": rng.uniform(0.02, 0.15)}
    total = sum(raw.values())
    return {k: round(v / total, 4) for k, v in raw.items()}


def draw_specs(count: int, seed: int, prefix: str) -> list:
    """`count` junction specs (see traffic_drl.intake), stratified over the heavy-axis rate within each pattern
    kind so the whole range from quiet to near capacity is covered, then jittered per road."""
    rng = random.Random(seed)
    per_kind = math.ceil(count / len(KINDS))
    slots = {k: rng.sample(range(per_kind), per_kind) for k in KINDS}
    specs = []
    for i in range(count):
        kind = KINDS[i % len(KINDS)]
        u = (slots[kind][i // len(KINDS)] + rng.random()) / per_kind
        heavy = math.exp(math.log(RATE_RANGE[0]) + u * (math.log(RATE_RANGE[1]) - math.log(RATE_RANGE[0])))
        light = heavy * rng.uniform(0.85, 1.0) if kind == "balanced" else heavy / rng.uniform(2.0, 6.0)
        ns, ew = (heavy, light) if rng.random() < 0.5 else (light, heavy)
        rates = {a: max(20, int(round(r * rng.uniform(0.8, 1.2), -1)))
                 for a, r in (("north", ns), ("south", ns), ("east", ew), ("west", ew))}
        spec = {"name": f"{prefix}_{i:02d}", "description": f"{kind} pattern, heavy axis about {heavy:.0f} veh/h",
                "demand": _demand(rates, kind == "flipping"), "vehicle_mix": _mix(rng)}
        if rng.random() > 0.25:
            spec["turns"] = {"left": round(rng.uniform(0.0, 0.2), 2), "right": round(rng.uniform(0.0, 0.2), 2)}
        if not isinstance(spec["demand"], list):
            spec["duration_minutes"] = 30
        specs.append(spec)
    return specs


def preset_specs() -> list:
    return [{"name": name, "description": "web app starting point, default mix and turning",
             "demand": _demand(rates, swap), "vehicle_mix": dict(DEFAULT_MIX), "turns": {"left": 0.1, "right": 0.1},
             **({} if swap else {"duration_minutes": 30})} for name, (rates, swap) in PRESETS.items()]


def write_pool(out_dir: str, specs: list) -> list:
    """Write each spec as a scenario (yaml + route file) into `out_dir`, plus specs.json; returns the scenario yaml paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = [intake.build_scenario(s, out_dir)["scenario_yaml"] for s in specs]
    with open(os.path.join(out_dir, "specs.json"), "w") as f:
        json.dump(specs, f, indent=1)
    return paths
