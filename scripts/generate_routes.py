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

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"/>
{routes}
{flows}
</routes>
"""


def build_flows(args) -> list:
    if not args.tidal:
        return [
            f'    <flow id="flow_{rid}" type="car" route="{rid}" begin="0" end="{args.end}" '
            f'vehsPerHour="{args.vehs_per_hour}"/>'
            for rid, _ in ROUTES
        ]
    high, low = args.tidal
    flows, k, begin = [], 0, 0.0
    while begin < args.end:
        end = min(begin + args.period, args.end)
        ns_heavy = k % 2 == 0
        for rid, _ in ROUTES:
            rate = high if (AXIS[rid] == "NS") == ns_heavy else low
            flows.append(f'    <flow id="flow_{rid}_{k}" type="car" route="{rid}" begin="{begin:g}" '
                         f'end="{end:g}" vehsPerHour="{rate:g}"/>')
        k, begin = k + 1, end
    return flows


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
    args = parser.parse_args()

    route_xml = "\n".join(f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in ROUTES)
    flow_xml = "\n".join(build_flows(args))

    with open(args.out, "w") as f:
        f.write(TEMPLATE.format(routes=route_xml, flows=flow_xml))
    what = (f"tidal {args.tidal[0]:g}/{args.tidal[1]:g} veh/h per approach, period {args.period:g}s"
            if args.tidal else f"{args.vehs_per_hour} veh/h per approach")
    print(f"Wrote {args.out} ({what}, over {args.end}s)")


if __name__ == "__main__":
    main()
