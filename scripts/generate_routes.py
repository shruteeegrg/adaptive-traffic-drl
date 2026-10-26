#!/usr/bin/env python3
"""Generate a SUMO route file (.rou.xml) for the single intersection network.

Only straight-through movements are modelled for Week 2 (East<->West,
North<->South) -- turning movements are a deliberate later enhancement,
once the basic environment loop (Week 2) and the agent (Weeks 3-6) are
proven out. This mirrors the proposal's own risk mitigation: master the
simplest version of the simulator/agent loop before adding complexity.

Usage:
    python scripts/generate_routes.py --out configs/intersection.rou.xml --vehs-per-hour 300
    python scripts/generate_routes.py --out configs/scenarios/rush_hour.rou.xml --vehs-per-hour 900
    python scripts/generate_routes.py --out configs/scenarios/low_traffic.rou.xml --vehs-per-hour 120
    python scripts/generate_routes.py --out configs/scenarios/tidal.rou.xml --tidal 1100 300 --period 900

Kathmandu-style traffic (added for the realistic scenarios):
    --fleet kathmandu   mixed vehicle types (about 62% motorcycles, 22% cars, 8% buses, 8% light goods)
    --turns 0.15 0.15   fraction of each approach's vehicles turning left / right (default straight only)
    python scripts/generate_routes.py --out configs/scenarios/kathmandu_peak.rou.xml --vehs-per-hour 1100 --fleet kathmandu --turns 0.15 0.15

--tidal HIGH LOW makes demand uneven and time-varying: in alternating
periods one axis gets HIGH veh/h per approach and the other LOW, swapping
every --period seconds (north-south heavy first). A fixed 50/50 timer
cannot serve that well; an adaptive controller can shift green time toward
the heavy axis, so this is the scenario where adaptive control has something
to win.
"""
import argparse

# (route_id, edge sequence) -- each is "incoming boundary edge -> outgoing
# boundary edge" through the centre junction A1, per the node layout in
# generate_network.sh (B1=east, B2=north, B3=west, B4=south).
AXIS = {"east_west": "EW", "west_east": "EW", "north_south": "NS", "south_north": "NS"}
ROUTES = [
    ("east_west", "B1A1 A1B3"),
    ("west_east", "B3A1 A1B1"),
    ("north_south", "B2A1 A1B4"),
    ("south_north", "B4A1 A1B2"),
]

# Turning movements, taken from the connections in configs/intersection.net.xml
# (dir="r" / "l" for each incoming edge). Names are <straight route>_right / _left.
TURN_ROUTES = [
    ("east_west_right", "B1A1 A1B2", "east_west"), ("east_west_left", "B1A1 A1B4", "east_west"),
    ("west_east_right", "B3A1 A1B4", "west_east"), ("west_east_left", "B3A1 A1B2", "west_east"),
    ("north_south_right", "B2A1 A1B3", "north_south"), ("north_south_left", "B2A1 A1B1", "north_south"),
    ("south_north_right", "B4A1 A1B1", "south_north"), ("south_north_left", "B4A1 A1B3", "south_north"),
]
for _rid, _edges, _base in TURN_ROUTES:
    AXIS[_rid] = AXIS[_base]

# Vehicle mix for Kathmandu-style traffic. The shares follow the motorcycle-dominated fleet
# quoted in the project plan (MOPIT 2023: roughly 62/22/8/8) and are ASSUMPTIONS until checked
# against the source. Physical parameters are plausible SUMO values, not measured ones.
# Without SUMO's sublane model, motorcycles still queue in single file: they take less road
# (shorter, smaller gap) but do not filter between vehicles. That is a stated limitation.
FLEET = [
    ("motorcycle", 0.62, 'accel="3.0" decel="5.0" sigma="0.5" length="2.2" width="0.8" minGap="1.0" maxSpeed="13.9" vClass="motorcycle"'),
    ("car", 0.22, 'accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"'),
    ("bus", 0.08, 'accel="1.2" decel="4.0" sigma="0.5" length="12" width="2.5" minGap="2.5" maxSpeed="11.0" vClass="bus"'),
    ("goods", 0.08, 'accel="2.0" decel="4.0" sigma="0.5" length="6.5" width="2.1" minGap="2.5" maxSpeed="12.5" vClass="delivery"'),
]

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
{types}
{routes}
{flows}
</routes>
"""


def _movements(rid: str, rate: float, turns, vtype: str, suffix: str, begin, end) -> list:
    """Flows for one approach: straight plus (optionally) left and right turns that split `rate`."""
    left, right = turns
    parts = [(rid, rate * (1.0 - left - right))]
    if left > 0:
        parts.append((f"{rid}_left", rate * left))
    if right > 0:
        parts.append((f"{rid}_right", rate * right))
    return [f'    <flow id="flow_{route}{suffix}" type="{vtype}" route="{route}" begin="{begin:g}" '
            f'end="{end:g}" vehsPerHour="{r:g}"/>' for route, r in parts]


def build_flows(args) -> list:
    turns = tuple(getattr(args, "turns", None) or (0.0, 0.0))
    if min(turns) < 0 or sum(turns) >= 1:
        raise ValueError("--turns LEFT RIGHT must be non-negative fractions that sum to less than 1")
    vtype = "kt" if getattr(args, "fleet", None) else "car"
    flows = []
    if not args.tidal:
        for rid, _ in ROUTES:
            flows += _movements(rid, args.vehs_per_hour, turns, vtype, "", 0, args.end)
        return flows
    high, low = args.tidal
    k, begin = 0, 0.0
    while begin < args.end:
        end = min(begin + args.period, args.end)
        ns_heavy = k % 2 == 0
        for rid, _ in ROUTES:
            rate = high if (AXIS[rid] == "NS") == ns_heavy else low
            flows += _movements(rid, rate, turns, vtype, f"_{k}", begin, end)
        k, begin = k + 1, end
    return flows


def build_types(args) -> str:
    if not getattr(args, "fleet", None):
        return '    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"/>'
    lines = ['    <vTypeDistribution id="kt">']
    lines += [f'        <vType id="{n}" probability="{p}" {attrs}/>' for n, p, attrs in FLEET]
    lines.append("    </vTypeDistribution>")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output .rou.xml path")
    parser.add_argument(
        "--vehs-per-hour",
        type=float,
        default=300,
        help="Vehicles per hour, applied to each of the 4 approaches equally (default: 300)",
    )
    parser.add_argument(
        "--end", type=float, default=3600, help="Demand end time in seconds (default: 3600, i.e. 1 simulated hour)"
    )
    parser.add_argument("--tidal", type=float, nargs=2, metavar=("HIGH", "LOW"),
                        help="Alternate heavy/light demand between the NS and EW axes (veh/h per approach)")
    parser.add_argument("--period", type=float, default=900, help="Seconds per tidal period (default: 900)")
    parser.add_argument("--fleet", choices=["kathmandu"], help="Mixed vehicle types instead of cars only")
    parser.add_argument("--turns", type=float, nargs=2, metavar=("LEFT", "RIGHT"),
                        help="Fraction of each approach turning left and right (default: all straight)")
    args = parser.parse_args()

    all_routes = ROUTES + ([(r, e) for r, e, _ in TURN_ROUTES] if args.turns and sum(args.turns) > 0 else [])
    route_xml = "\n".join(f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in all_routes)
    flow_xml = "\n".join(build_flows(args))

    with open(args.out, "w") as f:
        f.write(TEMPLATE.format(types=build_types(args), routes=route_xml, flows=flow_xml))
    what = (f"tidal {args.tidal[0]:g}/{args.tidal[1]:g} veh/h per approach, period {args.period:g}s"
            if args.tidal else f"{args.vehs_per_hour} veh/h per approach")
    what += (f", {args.fleet} fleet" if args.fleet else "") + (f", turns L/R {args.turns[0]:g}/{args.turns[1]:g}" if args.turns else "")
    print(f"Wrote {args.out} ({what}, over {args.end}s)")


if __name__ == "__main__":
    main()
