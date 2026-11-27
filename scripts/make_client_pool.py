#!/usr/bin/env python3
"""Write the client-style traffic pools used to train and test the generalist agent.

    python scripts/make_client_pool.py --out-dir configs/scenarios/client_pool

train: 30 scenarios (what the agent learns on)      select: 8 (picks checkpoints and seeds)
test:  12 random + the 5 web-app presets (never used for any choice)
The three draws use different seeds and names, so no scenario appears in two of them.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from traffic_drl import pool  # noqa: E402

SEEDS = {"train": 101, "select": 202, "test": 303}
COUNTS = {"train": 30, "select": 8, "test": 12}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="configs/scenarios/client_pool")
    args = ap.parse_args()
    for split in ("train", "select", "test"):
        specs = pool.draw_specs(COUNTS[split], SEEDS[split], split)
        if split == "test":
            specs += pool.preset_specs()
        paths = pool.write_pool(os.path.join(args.out_dir, split), specs)
        print(f"{split}: {len(paths)} scenarios in {os.path.join(args.out_dir, split)}")


if __name__ == "__main__":
    main()
