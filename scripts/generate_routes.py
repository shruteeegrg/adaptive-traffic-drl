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
"""
import argparse

# (route_id, edge sequence) -- each is "incoming boundary edge -> outgoing
# boundary edge" through the centre junction A1, per the node layout in
# generate_network.sh (B1=east, B2=north, B3=west, B4=south).
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
    args = parser.parse_args()

    route_xml = "\n".join(f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in ROUTES)
    flow_xml = "\n".join(
        f'    <flow id="flow_{rid}" type="car" route="{rid}" begin="0" end="{args.end}" '
        f'vehsPerHour="{args.vehs_per_hour}"/>'
        for rid, _ in ROUTES
    )

    with open(args.out, "w") as f:
        f.write(TEMPLATE.format(routes=route_xml, flows=flow_xml))
    print(f"Wrote {args.out} ({args.vehs_per_hour} veh/h per approach, over {args.end}s)")


if __name__ == "__main__":
    main()
