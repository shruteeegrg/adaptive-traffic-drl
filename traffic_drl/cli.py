"""CLI entry point for the traffic-drl package.

Usage (once implemented):
    traffic-drl train --agent {qtable,dqn} --config configs/<name>.yaml
    traffic-drl evaluate --checkpoint checkpoints/dqn_final.pt --scenario configs/scenarios/rush_hour.yaml
    traffic-drl compare --config configs/<name>.yaml --scenarios rush_hour,low_traffic
    traffic-drl demo

Each subcommand should stay a thin wrapper around traffic_drl.env /
traffic_drl.agent / traffic_drl.baseline / traffic_drl.viz — the CLI itself
should not contain simulation or training logic.

Build order (see README.md 10-week plan):
  Week 1: this stub + argument parsing skeleton (no-op subcommands is fine)
  Week 3: `train --agent qtable` wired to a real agent
  Week 5: `train --agent dqn` wired to a real agent
  Week 7: `evaluate` wired to traffic_drl.viz for saved-log plotting
  Week 8: `compare` wired to traffic_drl.baseline + scenario configs
  Week 8: `demo` wired to traffic_drl.app (Streamlit)
"""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="traffic-drl")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="Train an agent (qtable or dqn)")
    train.add_argument("--agent", choices=["qtable", "dqn"], required=True)
    train.add_argument("--config", required=True, help="Path to intersection config YAML")

    evaluate = sub.add_parser("evaluate", help="Evaluate a trained checkpoint on a scenario")
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--scenario", required=True, help="Path to scenario config YAML")

    compare = sub.add_parser("compare", help="Compare DQN agent vs. fixed-time baseline")
    compare.add_argument("--config", required=True)
    compare.add_argument("--scenarios", required=True, help="Comma-separated scenario names")

    sub.add_parser("demo", help="Launch the interactive Streamlit demo app")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "train":
        print(f"[stub] would train agent={args.agent} config={args.config}")
    elif args.command == "evaluate":
        print(f"[stub] would evaluate checkpoint={args.checkpoint} scenario={args.scenario}")
    elif args.command == "compare":
        print(f"[stub] would compare config={args.config} scenarios={args.scenarios}")
    elif args.command == "demo":
        print("[stub] would launch: streamlit run traffic_drl/app.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
