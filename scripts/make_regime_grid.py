#!/usr/bin/env python3
"""Write the demand-by-unevenness grid used for the regime map (cars, straight movements, no flipping).

    python scripts/make_regime_grid.py --out-dir configs/scenarios/grid

Cell grid_d{D}_r{R}: the two axes together average D veh/h per approach, and the north-south axis
carries R times the east-west demand (R = 1 is the balanced case). Run all cells with
    traffic-drl compare --config configs/dqn_v_dqfd.yaml --scenarios <the printed names> --controller fixed ... --reference fixed
and draw the map with scripts/plot_regime_map.py.
"""
import argparse
import importlib.util
import os
from argparse import Namespace

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("generate_routes", os.path.join(HERE, "generate_routes.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

DEMANDS = (200, 400, 600, 800)
RATIOS = (1, 2, 4, 8)


def axis_rates(demand: float, ratio: float):
    """(NS, EW) veh/h per approach with mean `demand` and NS = ratio * EW."""
    return round(2.0 * demand * ratio / (1.0 + ratio), -1), round(2.0 * demand / (1.0 + ratio), -1)


def cell_name(demand, ratio) -> str:
    return f"grid_d{demand}_r{ratio}"


def write_grid(out_dir: str, demands=DEMANDS, ratios=RATIOS, end: float = 3600.0) -> list:
    os.makedirs(out_dir, exist_ok=True)
    names = []
    for d in demands:
        for r in ratios:
            ns, ew = axis_rates(d, r)
            name = cell_name(d, r)
            args = Namespace(tidal=None, vehs_per_hour=0, end=end, period=end, axis_demand=[ns, ew], fleet=None, turns=None)
            route_xml = "\n".join(f'    <route id="{rid}" edges="{edges}"/>' for rid, edges in gen.ROUTES)
            with open(os.path.join(out_dir, f"{name}.rou.xml"), "w") as f:
                f.write(gen.TEMPLATE.format(types=gen.build_types(args), routes=route_xml, flows="\n".join(gen.build_flows(args))))
            with open(os.path.join(out_dir, f"{name}.yaml"), "w") as f:
                f.write(f"# Regime-map cell: mean {d} veh/h per approach, NS = {r} x EW (NS {ns:g}, EW {ew:g}). Regenerate the grid with\n"
                        f"#   python scripts/make_regime_grid.py --out-dir <dir>\n"
                        f"name: {name}\n"
                        f"description: demand {d} veh/h per approach on average, NS carries {r} times the EW demand (NS {ns:g}, EW {ew:g}).\n"
                        f"route_file: {name}.rou.xml\n")
            names.append(name)
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True)
    a = parser.parse_args()
    names = write_grid(a.out_dir)
    print(f"wrote {len(names)} cells to {a.out_dir}")
    print(",".join(os.path.join(a.out_dir, n + ".yaml") for n in names))


if __name__ == "__main__":
    main()
