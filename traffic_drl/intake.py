"""Junction intake: turn a client's description of their traffic into a scenario the simulator can run.

A client does not write SUMO route files. They fill in a short spec (YAML or a dict): traffic counts per
approach road (constant, or a sequence of time periods), the vehicle mix and the share of turning vehicles.
`build_scenario` validates it and writes a route file plus a scenario YAML in the same format as
configs/scenarios/*.yaml, so the result drops straight into `traffic-drl compare`, `evaluate` and the demo.

    name: my_junction
    duration_minutes: 30            # used when `demand` is a single set of rates
    vehicle_mix: mixed              # cars | mixed | {motorcycle: 0.5, car: 0.3, bus: 0.1, goods: 0.1}
    turns: {left: 0.1, right: 0.1}  # share of each approach's vehicles turning (default: all straight)
    demand:                         # vehicles per hour on each approach road
      east: 600
      north: 900
      west: 600
      south: 900
    # ...or demand as time periods (a rush hour that builds, a tidal swing):
    # demand:
    #   - {minutes: 15, east: 300, north: 1100, west: 300, south: 1100}
    #   - {minutes: 15, east: 1100, north: 300, west: 1100, south: 300}

Scope (stated, not hidden): the junction itself is the project's single four-way, one-lane-per-road,
two-phase layout; intake describes the demand on it. Other junction geometries need a new network file
and a phase table (see traci_env.GREEN_PHASES).
"""

import os
from pathlib import Path

import yaml

APPROACHES = ("east", "north", "west", "south")
# approach (incoming road) -> the straight-through route that starts there, and its turning routes.
# Edges come from configs/intersection.net.xml (B1 = east, B2 = north, B3 = west, B4 = south).
STRAIGHT = {"east": ("east_west", "B1A1 A1B3"), "west": ("west_east", "B3A1 A1B1"),
            "north": ("north_south", "B2A1 A1B4"), "south": ("south_north", "B4A1 A1B2")}
TURNS = {"east": {"right": "B1A1 A1B2", "left": "B1A1 A1B4"}, "west": {"right": "B3A1 A1B4", "left": "B3A1 A1B2"},
         "north": {"right": "B2A1 A1B3", "left": "B2A1 A1B1"}, "south": {"right": "B4A1 A1B1", "left": "B4A1 A1B3"}}
AXIS = {"east": "EW", "west": "EW", "north": "NS", "south": "NS"}

# Vehicle types (same physical parameters as scripts/generate_routes.py; plausible SUMO values, not measured).
VTYPES = {
    "motorcycle": 'accel="3.0" decel="5.0" sigma="0.5" length="2.2" width="0.8" minGap="1.0" maxSpeed="13.9" vClass="motorcycle"',
    "car": 'accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"',
    "bus": 'accel="1.2" decel="4.0" sigma="0.5" length="12" width="2.5" minGap="2.5" maxSpeed="11.0" vClass="bus"',
    "goods": 'accel="2.0" decel="4.0" sigma="0.5" length="6.5" width="2.1" minGap="2.5" maxSpeed="12.5" vClass="delivery"',
}
MIXED = {"motorcycle": 0.62, "car": 0.22, "bus": 0.08, "goods": 0.08}   # the Kathmandu-style assumption used elsewhere
SATURATION_FLOW = 1800.0   # veh/h of green for one lane of cars: the usual planning figure (an assumption)
MAX_DEMAND = 3000.0        # veh/h per approach; above this a typo is more likely than a real single-lane road


class SpecError(ValueError):
    """The junction spec is not usable; the message says what to fix."""


def load_spec(path: str) -> dict:
    with open(path) as f:
        spec = yaml.safe_load(f)
    if not isinstance(spec, dict):
        raise SpecError(f"{path}: expected a YAML mapping with at least `name` and `demand`")
    return spec


def _rates(entry: dict, where: str) -> dict:
    unknown = set(entry) - set(APPROACHES) - {"minutes"}
    if unknown:
        raise SpecError(f"{where}: unknown keys {sorted(unknown)}; use {list(APPROACHES)}"
                        + (" and `minutes`" if "minutes" in entry else ""))
    rates = {}
    for a in APPROACHES:
        value = entry.get(a, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SpecError(f"{where}: {a} must be a number of vehicles per hour, got {value!r}")
        if value < 0 or value > MAX_DEMAND:
            raise SpecError(f"{where}: {a} = {value} veh/h is outside 0 to {MAX_DEMAND:g}")
        rates[a] = float(value)
    return rates


def _periods(spec: dict) -> list:
    """[(minutes, {approach: veh/h})] from either demand form."""
    demand = spec.get("demand")
    if demand is None:
        raise SpecError("the spec needs a `demand` section")
    if isinstance(demand, dict):
        minutes = spec.get("duration_minutes", 30)
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes <= 0:
            raise SpecError("duration_minutes must be a positive number")
        return [(float(minutes), _rates(demand, "demand"))]
    if isinstance(demand, list) and demand:
        periods = []
        for i, entry in enumerate(demand, start=1):
            where = f"demand period {i}"
            if not isinstance(entry, dict) or "minutes" not in entry:
                raise SpecError(f"{where}: each period needs `minutes` and the rates per approach")
            minutes = entry["minutes"]
            if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or minutes <= 0:
                raise SpecError(f"{where}: minutes must be a positive number")
            periods.append((float(minutes), _rates(entry, where)))
        return periods
    raise SpecError("`demand` must be a mapping of approach -> veh/h, or a non-empty list of periods")


def _mix(spec: dict) -> dict:
    mix = spec.get("vehicle_mix", "cars")
    if mix == "cars":
        return {"car": 1.0}
    if mix == "mixed":
        return dict(MIXED)
    if isinstance(mix, dict):
        unknown = set(mix) - set(VTYPES)
        if unknown:
            raise SpecError(f"vehicle_mix: unknown types {sorted(unknown)}; use {list(VTYPES)}")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 for v in mix.values()):
            raise SpecError("vehicle_mix: shares must be non-negative numbers")
        total = sum(mix.values())
        if abs(total - 1.0) > 0.01:
            raise SpecError(f"vehicle_mix: shares must add up to 1, they add up to {total:g}")
        return {k: v / total for k, v in mix.items() if v > 0}
    raise SpecError("vehicle_mix must be 'cars', 'mixed' or a mapping of type -> share")


def _turns(spec: dict) -> tuple:
    t = spec.get("turns") or {}
    unknown = set(t) - {"left", "right"}
    if unknown:
        raise SpecError(f"turns: unknown keys {sorted(unknown)}; use left and right")
    left, right = t.get("left", 0.0), t.get("right", 0.0)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 for v in (left, right)) or left + right >= 1:
        raise SpecError("turns: left and right must be non-negative shares that add up to less than 1")
    return float(left), float(right)


def check_name(name) -> str:
    if not isinstance(name, str) or not name or not all(c.isalnum() or c in "_-" for c in name):
        raise SpecError("`name` must be letters, digits, '_' or '-' (it becomes a file name)")
    return name


def demand_summary(periods: list) -> dict:
    """Planning numbers a client can sanity-check: total vehicles, and how loaded the junction is.

    `load` is the critical flow ratio, the heavier road of each axis over the saturation flow, summed
    across the two axes (each needs its share of the green). Below about 0.85 a good signal plan copes;
    from 0.9 the junction is close to capacity; above 1 it cannot clear the demand whatever the controller does."""
    hours = sum(m for m, _ in periods) / 60.0
    total = sum(sum(r.values()) * m / 60.0 for m, r in periods)
    worst = 0.0
    for _, r in periods:
        ns = max(r["north"], r["south"]) / SATURATION_FLOW
        ew = max(r["east"], r["west"]) / SATURATION_FLOW
        worst = max(worst, ns + ew)
    return {"minutes": hours * 60.0, "vehicles": total, "peak_load": worst}


def advisories(summary: dict, periods: list) -> list:
    notes = []
    load = summary["peak_load"]
    if load > 1.0:
        notes.append(f"Demand exceeds what one lane per road can discharge (load {load:.2f} > 1). Queues will grow "
                     "under any controller; expect little difference between controllers.")
    elif load > 0.9:
        notes.append(f"The junction is close to capacity (load {load:.2f}). Gains from a smarter signal are "
                     "limited and results are sensitive to the traffic's randomness.")
    elif load < 0.15:
        notes.append(f"Traffic is very light (load {load:.2f}). Almost any controller will keep vehicles moving.")
    if summary["minutes"] > 60:
        notes.append("The demand is longer than 60 minutes; the evaluation episode length in the config "
                     "(episode_length) must cover it or the tail of the demand is never simulated.")
    return notes


def build_scenario(spec: dict, out_dir: str) -> dict:
    """Validate `spec`, write <name>.rou.xml and <name>.yaml into `out_dir`, return a summary:
    {"name", "scenario_yaml", "route_file", "summary", "advisories"}."""
    name = check_name(spec.get("name"))
    unknown = set(spec) - {"name", "description", "duration_minutes", "vehicle_mix", "turns", "demand"}
    if unknown:
        raise SpecError(f"unknown top-level keys {sorted(unknown)}")
    periods, mix, (left, right) = _periods(spec), _mix(spec), _turns(spec)

    if len(mix) == 1:
        (vtype,) = mix
        types = f'    <vType id="{vtype}" {VTYPES[vtype]}/>'
    else:
        vtype = "mix"
        lines = ['    <vTypeDistribution id="mix">']
        lines += [f'        <vType id="{k}" probability="{p:.6f}" {VTYPES[k]}/>' for k, p in mix.items()]
        lines.append("    </vTypeDistribution>")
        types = "\n".join(lines)

    routes = [f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in STRAIGHT.values()]
    if left or right:
        for a, (rid, _) in STRAIGHT.items():
            routes += [f'    <route id="{rid}_{side}" edges="{edges}"/>' for side, edges in TURNS[a].items()
                       if (left if side == "left" else right) > 0]

    flows, begin = [], 0.0
    for k, (minutes, rates) in enumerate(periods):
        end = begin + minutes * 60.0
        for a, (rid, _) in STRAIGHT.items():
            if rates[a] <= 0:
                continue
            parts = [(rid, rates[a] * (1.0 - left - right))]
            if left:
                parts.append((f"{rid}_left", rates[a] * left))
            if right:
                parts.append((f"{rid}_right", rates[a] * right))
            flows += [f'    <flow id="flow_{route}_{k}" type="{vtype}" route="{route}" begin="{begin:g}" '
                      f'end="{end:g}" vehsPerHour="{r:g}"/>' for route, r in parts]
        begin = end

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n'
           + types + "\n" + "\n".join(routes) + "\n" + "\n".join(flows) + "\n</routes>\n")

    summary = demand_summary(periods)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    route_path, yaml_path = out / f"{name}.rou.xml", out / f"{name}.yaml"
    route_path.write_text(xml)
    description = spec.get("description") or (
        f"{summary['vehicles']:.0f} vehicles over {summary['minutes']:.0f} minutes (generated by traffic-drl intake)")
    yaml_path.write_text(yaml.safe_dump({"name": name, "description": description, "route_file": route_path.name},
                                        sort_keys=False))
    return {"name": name, "scenario_yaml": str(yaml_path), "route_file": str(route_path),
            "summary": summary, "advisories": advisories(summary, periods)}


def build_from_file(spec_path: str, out_dir: str = None) -> dict:
    spec = load_spec(spec_path)
    return build_scenario(spec, out_dir or os.path.join("projects", str(spec.get("name", "junction"))))
