"""CLI entry point for the traffic-drl package.

Usage:
    traffic-drl env-check --config configs/intersection.yaml
    traffic-drl train --agent {qtable,dqn} --config configs/<name>.yaml
    traffic-drl evaluate --checkpoint checkpoints/dqn_final.pt --scenario configs/scenarios/rush_hour.yaml
    traffic-drl compare --config configs/<name>.yaml --scenarios rush_hour,low_traffic
    traffic-drl sweep --config configs/dqn.yaml --scenario configs/scenarios/rush_hour.yaml
    traffic-drl demo

Each subcommand should stay a thin wrapper around traffic_drl.env /
traffic_drl.agent / traffic_drl.baseline / traffic_drl.viz — the CLI itself
should not contain simulation or training logic.

Build order (see README.md 10-week plan):
  Week 1: CLI skeleton (no-op subcommands)
  Week 2: `env-check` wired to traffic_drl.env.TraciEnv (real, not a stub)
  Week 3: `train --agent qtable` wired to a real agent
  Week 5: `train --agent dqn` wired to a real agent (done)
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
    train.add_argument("--env", choices=["sumo", "toy"], default="sumo",
                       help="sumo = TraciEnv (needs SUMO); toy = fast pure-Python queue model")
    train.add_argument("--scenario", help="Scenario YAML (e.g. configs/scenarios/rush_hour.yaml); SUMO env only")
    train.add_argument("--episodes", type=int, help="Override episodes from the config")
    train.add_argument("--out-dir", default="checkpoints", help="Where the checkpoint, log and plot go")
    train.add_argument("--eval-every", type=int, help="Greedy evaluation every N episodes (keeps a best checkpoint); overrides config")

    sweep = sub.add_parser("sweep", help="Hyperparameter sweep for the DQN agent across seeds (Week 6)")
    sweep.add_argument("--config", default="configs/dqn.yaml")
    sweep.add_argument("--scenario", help="Scenario YAML to train and evaluate on; SUMO env only")
    sweep.add_argument("--env", choices=["sumo", "toy"], default="sumo")
    sweep.add_argument("--episodes", type=int, help="Override sweep.episodes from the config")
    sweep.add_argument("--seeds", help="Comma-separated seeds, e.g. 0,1,2 (overrides sweep.seeds)")
    sweep.add_argument("--out-dir", default="sweep_results")

    evaluate = sub.add_parser("evaluate", help="Evaluate a trained checkpoint on a scenario")
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--scenario", required=True, help="Path to scenario config YAML")

    compare = sub.add_parser("compare", help="Compare DQN agent vs. fixed-time baseline")
    compare.add_argument("--config", required=True)
    compare.add_argument("--scenarios", required=True, help="Comma-separated scenario names")

    sub.add_parser("demo", help="Launch the interactive Streamlit demo app")

    env_check = sub.add_parser(
        "env-check", help="Sanity-check the SUMO/TraCI environment against a config (Week 2)"
    )
    env_check.add_argument("--config", default="configs/intersection.yaml")
    env_check.add_argument("--steps", type=int, default=200)
    env_check.add_argument("--scenario", help="Scenario YAML to run instead of the default demand")

    return parser


def _train(args) -> int:
    import os

    from traffic_drl.agent import DQNAgent, QTableAgent, train_agent
    from traffic_drl.config import load_config
    from traffic_drl.viz import plot_reward_curve

    config = load_config(args.config)
    section = "qtable" if args.agent == "qtable" else "dqn"
    params = config.get(section, {})
    episodes = args.episodes or params.get("episodes", 30)

    if args.env == "toy":
        from traffic_drl.env import SimpleQueueEnv

        if args.scenario:
            print("note: --scenario is ignored with --env toy")

        # The toy model's state is sized for the agent, not for the YAML.
        env = SimpleQueueEnv(seed=params.get("seed", 0), state_scale=20.0,
                             include_phase=args.agent == "dqn")
        state_size = env.state_size
    else:
        from traffic_drl.env import TraciEnv

        env = TraciEnv(args.config, scenario=args.scenario)
        state_size = env.state_size

    if args.agent == "qtable":
        agent = QTableAgent.from_config(config)
        ckpt_name = "qtable.json"
    else:
        agent = DQNAgent.from_config(config, state_dim=state_size)
        ckpt_name = "dqn.npz"

    os.makedirs(args.out_dir, exist_ok=True)
    log_path = os.path.join(args.out_dir, f"{args.agent}_rewards.csv")
    eval_every = args.eval_every if args.eval_every is not None else params.get("eval_every")
    stem, ext = os.path.splitext(ckpt_name)
    best_path = os.path.join(args.out_dir, f"{stem}_best{ext}") if eval_every else None
    history = {}
    try:
        train_agent(env, agent, episodes, max_steps=params.get("max_steps"), log_path=log_path,
                    eval_every=eval_every, best_path=best_path, history=history)
    finally:
        env.close()
    if best_path:
        print(f"best checkpoint: {best_path} (episode {history['best_episode']})")

    ckpt_path = os.path.join(args.out_dir, ckpt_name)
    agent.save(ckpt_path)
    plot_path = plot_reward_curve(log_path, os.path.join(args.out_dir, f"{args.agent}_reward_curve.png"))
    print(f"saved checkpoint={ckpt_path} log={log_path} plot={plot_path}")
    return 0


def _sweep(args) -> int:
    from traffic_drl.config import load_config
    from traffic_drl.sweep import run_sweep

    config = load_config(args.config)
    sw = config.get("sweep", {})
    if not sw.get("grid"):
        raise SystemExit(f"{args.config} has no sweep.grid section")
    episodes = args.episodes or sw.get("episodes", 40)
    seeds = [int(x) for x in args.seeds.split(",")] if args.seeds else sw.get("seeds", [0, 1])

    if args.env == "toy":
        from traffic_drl.env import SimpleQueueEnv

        env = SimpleQueueEnv(seed=0, state_scale=20.0, include_phase=True)
    else:
        from traffic_drl.env import TraciEnv

        env = TraciEnv(args.config, scenario=args.scenario)
    try:
        summary = run_sweep(env, config, sw["grid"], seeds, episodes, args.out_dir,
                            max_steps=config.get("dqn", {}).get("max_steps"),
                            eval_every=config.get("dqn", {}).get("eval_every"))
    finally:
        env.close()

    print("\nranked settings (best first):")
    for i, row in enumerate(summary, start=1):
        print(f"{i}. " + "  ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))
    print(f"\nwrote {args.out_dir}/sweep_summary.csv, sweep_runs.csv, runs/")
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "env-check":
        from traffic_drl.env import TraciEnv

        env = TraciEnv(args.config, scenario=args.scenario)
        state = env.reset()
        print(f"reset() OK — state shape {state.shape}, initial state {state}")
        total_reward = 0.0
        action = 0
        for i in range(args.steps):
            if i % 30 == 0:
                action = 1 - action
            state, reward, done, info = env.step(action)
            total_reward += reward
            if done:
                break
        metrics = env.metrics()
        env.close()
        print(f"metrics: mean_queue={metrics['mean_queue']:.2f} "
              f"avg_wait_per_vehicle={metrics['avg_wait_per_vehicle']:.1f}s "
              f"throughput_per_hour={metrics['throughput_per_hour']:.0f}")
        print(f"step() OK — ran {i + 1} steps, total_reward={total_reward:.1f}, final_state={state}")
    elif args.command == "train":
        return _train(args)
    elif args.command == "sweep":
        return _sweep(args)
    elif args.command == "evaluate":
        print(f"[stub] would evaluate checkpoint={args.checkpoint} scenario={args.scenario}")
    elif args.command == "compare":
        print(f"[stub] would compare config={args.config} scenarios={args.scenarios}")
    elif args.command == "demo":
        print("[stub] would launch: streamlit run traffic_drl/app.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
