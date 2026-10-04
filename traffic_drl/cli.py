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
  Week 6: `evaluate` runs a checkpoint on a scenario (pulled forward); Week 7 adds plotting
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

    baseline = sub.add_parser("baseline", help="Evaluate the fixed-time controller on a scenario (same metrics as the agents)")
    baseline.add_argument("--config", default="configs/dqn.yaml")
    baseline.add_argument("--scenario", help="Scenario YAML; SUMO env only")
    baseline.add_argument("--green", type=int, default=42, help="Green duration in seconds (default 42)")
    baseline.add_argument("--episodes", type=int, default=3)
    baseline.add_argument("--seed-base", type=int, default=10000, help="First SUMO seed for evaluation episodes")

    sweep = sub.add_parser("sweep", help="Hyperparameter sweep for the DQN agent across seeds (Week 6)")
    sweep.add_argument("--config", default="configs/dqn.yaml")
    sweep.add_argument("--scenario", help="Scenario YAML to train and evaluate on; SUMO env only")
    sweep.add_argument("--env", choices=["sumo", "toy"], default="sumo")
    sweep.add_argument("--episodes", type=int, help="Override sweep.episodes from the config")
    sweep.add_argument("--seeds", help="Comma-separated seeds, e.g. 0,1,2 (overrides sweep.seeds)")
    sweep.add_argument("--out-dir", default="sweep_results")

    evaluate = sub.add_parser("evaluate", help="Evaluate a trained checkpoint on a scenario")
    evaluate.add_argument("--checkpoint", required=True)
    evaluate.add_argument("--scenario", help="Path to scenario config YAML (default: the config's own demand)")
    evaluate.add_argument("--config", default="configs/dqn.yaml",
                          help="Config the checkpoint was trained with (state design, network size)")
    evaluate.add_argument("--episodes", type=int, default=3)
    evaluate.add_argument("--seed-base", type=int, default=10000,
                          help="First SUMO seed for evaluation episodes (use a fresh value to avoid seeds used for selection)")

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


def _toy_env(agent: str, seed: int):
    """Toy queue model sized for the agent: the DQN wants scaled inputs and
    scaled rewards; the Q-table wants raw queue counts for its buckets."""
    from traffic_drl.env import SimpleQueueEnv

    dqn = agent == "dqn"
    return SimpleQueueEnv(seed=seed, include_phase=True,
                          state_scale=20.0 if dqn else 1.0, reward_scale=30.0 if dqn else 1.0)


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
        if args.scenario:
            print("note: --scenario is ignored with --env toy")

        # The toy model's state is sized for the agent, not for the YAML.
        env = _toy_env(args.agent, params.get("seed", 0))
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


def _evaluate(args) -> int:
    import csv
    import glob
    import os

    from traffic_drl.agent import DQNAgent, QTableAgent, evaluate
    from traffic_drl.config import load_config
    from traffic_drl.env import TraciEnv

    # A directory means: score every *_best.npz inside it (e.g. a sweep's runs/).
    if os.path.isdir(args.checkpoint):
        paths = sorted(glob.glob(os.path.join(args.checkpoint, "**", "*_best.npz"), recursive=True))
        if not paths:
            raise SystemExit(f"no *_best.npz checkpoints under {args.checkpoint}")
    else:
        paths = [args.checkpoint]

    config = load_config(args.config)
    env = TraciEnv(args.config, scenario=args.scenario)
    table = []
    try:
        for path in paths:
            agent = (QTableAgent.from_config(config) if path.endswith(".json")
                     else DQNAgent.from_config(config, state_dim=env.state_size))
            try:
                agent.load(path)
            except ValueError as e:
                raise SystemExit(f"{e}\n(is --config the config this checkpoint was trained with?)")
            results = [evaluate(env, agent, episodes=1, seed_base=args.seed_base) for _ in range(args.episodes)]
            mean = {k: sum(r[k] for r in results) / len(results) for k in results[0]}
            table.append((path, results, mean))
    finally:
        env.close()

    where = args.scenario or "default demand"
    if len(table) == 1:
        path, results, mean = table[0]
        print(f"{path} on {where}, {args.episodes} episodes, seeds from {args.seed_base}:")
        for i, r in enumerate(results, start=1):
            print(f"  episode {i}: " + "  ".join(f"{k}={r[k]:.2f}" for k in r))
        print("  mean:      " + "  ".join(f"{k}={v:.2f}" for k, v in mean.items()))
        return 0

    table.sort(key=lambda row: row[2].get("mean_total_waiting", -row[2]["reward"]))
    print(f"{len(table)} checkpoints on {where}, {args.episodes} episodes each, ranked by mean_total_waiting:")
    for path, _, mean in table:
        print(f"  {os.path.basename(path)}: " + "  ".join(
            f"{k}={mean[k]:.1f}" for k in ("mean_total_waiting", "throughput_per_hour", "switches") if k in mean))
    out = os.path.join(args.checkpoint, "best_checkpoints_eval.csv")
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["checkpoint", *table[0][2].keys()])
        for path, _, mean in table:
            writer.writerow([os.path.relpath(path, args.checkpoint), *mean.values()])
    print(f"wrote {out}")
    return 0


def _baseline(args) -> int:
    from traffic_drl.agent import evaluate
    from traffic_drl.baseline import FixedTimeAgent
    from traffic_drl.env import TraciEnv

    env = TraciEnv(args.config, scenario=args.scenario)
    green_steps = max(1, round(args.green / env.decision_interval))  # decisions per green
    agent = FixedTimeAgent(green_steps=green_steps)
    results = []
    try:
        for _ in range(args.episodes):
            agent.reset()
            results.append(evaluate(env, agent, episodes=1, seed_base=args.seed_base))
    finally:
        env.close()
    keys = results[0].keys()
    print(f"fixed-time baseline, green={green_steps * env.decision_interval:.0f}s "
          f"(requested {args.green}s, decision interval {env.decision_interval:.0f}s), "
          f"{args.episodes} episodes, seeds from {args.seed_base}:")
    for i, r in enumerate(results, start=1):
        print(f"  episode {i}: " + "  ".join(f"{k}={r[k]:.2f}" for k in keys))
    print("  mean:      " + "  ".join(f"{k}={sum(r[k] for r in results) / len(results):.2f}" for k in keys))
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

        env = _toy_env("dqn", 0)
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
              f"mean_backlog={metrics['mean_backlog']:.2f} "
              f"avg_wait_per_vehicle={metrics['avg_wait_per_vehicle']:.1f}s "
              f"throughput_per_hour={metrics['throughput_per_hour']:.0f}")
        print(f"step() OK — ran {i + 1} steps, total_reward={total_reward:.1f}, final_state={state}")
    elif args.command == "train":
        return _train(args)
    elif args.command == "baseline":
        return _baseline(args)
    elif args.command == "sweep":
        return _sweep(args)
    elif args.command == "evaluate":
        return _evaluate(args)
    elif args.command == "compare":
        print(f"[stub] would compare config={args.config} scenarios={args.scenarios}")
    elif args.command == "demo":
        print("[stub] would launch: streamlit run traffic_drl/app.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
