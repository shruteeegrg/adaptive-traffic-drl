#!/usr/bin/env python3
"""Write a pool of randomised-demand scenarios for training one model that must cope with many patterns.

    python scripts/make_scenario_pool.py --out-dir configs/scenarios/pool --count 12 --seed 7
    python scripts/make_scenario_pool.py --out-dir configs/scenarios/pool_kt --count 12 --seed 7 --fleet kathmandu --turns 0.15 0.15

Patterns are drawn in three kinds, in turn: balanced (both axes about equal), uneven (one axis 2 to 6 times
the other) and flipping (uneven, with the axes swapping at 900 s). The heavier axis gets 300 to 1300
veh/h per approach. Training cycles through the pool, so each episode is a different demand pattern. The
three named evaluation scenarios (low_traffic, rush_hour, tidal) are NOT in the pool; they stay held out.
"""
import argparse
import importlib.util
import math
import os
import random
import sys
from argparse import Namespace

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("generate_routes", os.path.join(HERE, "generate_routes.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

KINDS = ("balanced", "uneven", "flipping")
HEAVY_RANGE = (300.0, 1300.0)


def draw_patterns(count: int, seed: int) -> list:
    """[(kind, ns_rate, ew_rate, swaps)] with rates rounded to 10 veh/h."""
    rng = random.Random(seed)
    per_kind = math.ceil(count / len(KINDS))
    slots = {k: rng.sample(range(per_kind), per_kind) for k in KINDS}    # stratified: each kind spans the whole range
    out = []
    for i in range(count):
        kind = KINDS[i % len(KINDS)]
        u = (slots[kind][i // len(KINDS)] + rng.random()) / per_kind
        heavy = math.exp(math.log(HEAVY_RANGE[0]) + u * (math.log(HEAVY_RANGE[1]) - math.log(HEAVY_RANGE[0])))
        if kind == "balanced":
            light = heavy * rng.uniform(0.85, 1.0)
        else:
            light = heavy / rng.uniform(2.0, 6.0)
        ns, ew = (heavy, light) if rng.random() < 0.5 else (light, heavy)
        out.append((kind, round(ns, -1), round(ew, -1), kind == "flipping"))
    return out


def write_pool(out_dir: str, count: int, seed: int, end: float = 3600.0, fleet=None, turns=None) -> list:
    os.makedirs(out_dir, exist_ok=True)
    names = []
    for i, (kind, ns, ew, swaps) in enumerate(draw_patterns(count, seed)):
        name = f"pool_{i:02d}"
        period = 900.0 if swaps else end
        args = Namespace(tidal=None, vehs_per_hour=0, end=end, period=period, axis_demand=[ns, ew], fleet=fleet, turns=turns)
        all_routes = gen.ROUTES + ([(r, e) for r, e, _ in gen.TURN_ROUTES] if turns and sum(turns) > 0 else [])
        route_xml = "\n".join(f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in all_routes)
        with open(os.path.join(out_dir, f"{name}.rou.xml"), "w") as f:
            f.write(gen.TEMPLATE.format(types=gen.build_types(args), routes=route_xml, flows="\n".join(gen.build_flows(args))))
        with open(os.path.join(out_dir, f"{name}.yaml"), "w") as f:
            f.write(f"# Randomised-demand pool member ({kind}); regenerate the whole pool with\n"
                    f"#   python scripts/make_scenario_pool.py --out-dir <dir> --count {count} --seed {seed}\n"
                    f"name: {name}\n"
                    f"description: {kind}, NS {ns:g} / EW {ew:g} veh/h per approach{', axes swap every 900 s' if swaps else ''}.\n"
                    f"route_file: {name}.rou.xml\n")
        names.append(name)
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--fleet", choices=["kathmandu"])
    parser.add_argument("--turns", type=float, nargs=2, metavar=("LEFT", "RIGHT"))
    a = parser.parse_args()
    names = write_pool(a.out_dir, a.count, a.seed, fleet=a.fleet, turns=a.turns)
    for n, (kind, ns, ew, swaps) in zip(names, draw_patterns(a.count, a.seed)):
        print(f"{n}: {kind:9s} NS {ns:6g}  EW {ew:6g}{'  (swap at 900 s)' if swaps else ''}")


if __name__ == "__main__":
    sys.exit(main())
