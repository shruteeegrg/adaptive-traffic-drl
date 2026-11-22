"""CLI entry point for the traffic-drl package.

Usage:
    traffic-drl env-check --config configs/intersection.yaml
    traffic-drl train --agent {qtable,dqn} --config configs/<name>.yaml
    traffic-drl evaluate --checkpoint checkpoints/dqn_final.npz --scenario configs/scenarios/rush_hour.yaml
    traffic-drl compare --config configs/<name>.yaml --scenarios rush_hour,low_traffic
    traffic-drl sweep --config configs/dqn.yaml --scenario configs/scenarios/rush_hour.yaml
    traffic-drl plot training --log <log.csv> --out <fig.png>
    traffic-drl plot compare --item SCENARIO:LABEL=<results.csv> ... --out <fig.png>
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
  `demo` launches the Streamlit app (traffic_drl/app.py); `run` streams one controller's episode for it
"""

import argparse
import json
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="traffic-drl")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="Train an agent (qtable or dqn)")
    train.add_argument("--agent", choices=["qtable", "dqn"], required=True)
    train.add_argument("--config", required=True, help="Path to intersection config YAML")
    train.add_argument("--env", choices=["sumo", "toy"], default="sumo",
                       help="sumo = TraciEnv (needs SUMO); toy = fast pure-Python queue model")
    train.add_argument("--scenario", help="Scenario YAML, or several comma-separated to train on a mix "
                                          "(episodes cycle through them); SUMO env only")
    train.add_argument("--episodes", type=int, help="Override episodes from the config")
    train.add_argument("--out-dir", default="checkpoints", help="Where the checkpoint, log and plot go")
    train.add_argument("--eval-every", type=int, help="Greedy evaluation every N episodes (keeps a best checkpoint); overrides config")

    baseline = sub.add_parser("baseline", help="Evaluate the fixed-time controller on a scenario (same metrics as the agents)")
    baseline.add_argument("--config", default="configs/dqn.yaml")
    baseline.add_argument("--scenario", help="Scenario YAML; SUMO env only")
    baseline.add_argument("--green", type=int, default=42, help="Green duration in seconds (default 42)")
    baseline.add_argument("--episodes", type=int, default=3)
    baseline.add_argument("--save-csv", help="Write per-episode metrics to this CSV (for `plot compare`)")
    baseline.add_argument("--seed-base", type=int, default=10000, help="First SUMO seed for evaluation episodes")

    run = sub.add_parser("run", help="Run one controller on one scenario, streaming JSON-lines events (used by the demo app)")
    run.add_argument("--controller", choices=["fixed", "actuated", "dqn"], required=True)
    run.add_argument("--config", default="configs/dqn.yaml")
    run.add_argument("--scenario", help="Scenario YAML")
    run.add_argument("--checkpoint", default="checkpoints/dqn_final.npz", help="DQN checkpoint (dqn controller only)")
    run.add_argument("--seed", type=int, default=40000, help="SUMO seed (same seed = same traffic)")
    run.add_argument("--delay", type=float, default=0.0, help="Seconds to pause per decision, for watchable playback")
    run.add_argument("--green", type=int, default=42, help="Fixed-time green duration in seconds")
    run.add_argument("--out", required=True, help="JSON-lines output path")

    plot = sub.add_parser("plot", help="Draw charts from saved logs and results")
    plot_sub = plot.add_subparsers(dest="plot_kind", required=True)
    pt = plot_sub.add_parser("training", help="Training/evaluation curves from a training log CSV")
    pt.add_argument("--log", required=True, help="Training log CSV (e.g. checkpoints/dqn_rewards.csv)")
    pt.add_argument("--evals", help="Evaluation-history CSV (a sweep run's *_evals.csv)")
    pt.add_argument("--out", required=True, help="Output PNG")
    pt.add_argument("--title")
    pc = plot_sub.add_parser("compare", help="Controllers side by side from `--save-csv` results")
    pc.add_argument("--item", action="append", required=True, metavar="SCENARIO:LABEL=CSV",
                    help="One result file; repeat for each controller/scenario, e.g. "
                         "rush_hour:Fixed-time=base.csv  rush_hour:DQN=dqn.csv")
    pc.add_argument("--metrics", help="Comma-separated metric names (default: total waiting, throughput, switches)")
    pc.add_argument("--out", required=True, help="Output PNG")
    pc.add_argument("--title")

    sweep = sub.add_parser("sweep", help="Hyperparameter sweep for the DQN agent across seeds (Week 6)")
    sweep.add_argument("--config", default="configs/dqn.yaml")
    sweep.add_argument("--scenario", help="Scenario YAML(s) to train and evaluate on (comma-separate for a mix); SUMO env only")
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
    evaluate.add_argument("--save-csv", help="Write per-episode metrics to this CSV (single checkpoint only; for `plot compare`)")
    evaluate.add_argument("--seed-base", type=int, default=10000,
                          help="First SUMO seed for evaluation episodes (use a fresh value to avoid seeds used for selection)")

    compare = sub.add_parser("compare", help="Compare controllers on scenarios with confidence intervals and t-tests")
    compare.add_argument("--config", default="configs/dqn.yaml")
    compare.add_argument("--scenarios", required=True, help="Comma-separated scenario names or YAML paths")
    compare.add_argument("--controller", action="append", required=True, metavar="[NAME=]SPEC",
                         help="fixed[:GREEN_S] | actuated[:min=10,max=60,gap=1,ratio=1.5] | dqn:CHECKPOINT; repeat for each controller")
    compare.add_argument("--reference", help="Label of the controller the others are tested against (default: first)")
    compare.add_argument("--episodes", type=int, default=100, help="Episodes per controller per scenario (default 100)")
    compare.add_argument("--seed-base", type=int, default=30000, help="First SUMO seed (default 30000, unused in training)")
    compare.add_argument("--threshold", type=float, default=0.05, help="Practical-significance threshold, fraction of the reference mean (default 0.05)")
    compare.add_argument("--min-abs", type=float, default=None,
                         help="Also require this absolute change in the metric (default: 2 vehicles, or 1 s for avg_wait_per_vehicle)")
    compare.add_argument("--metric", default="mean_total_waiting",
                         help="Metric to test: mean_total_waiting (default), avg_wait_per_vehicle, throughput_per_hour, switches")
    compare.add_argument("--out-dir", default="results_compare")

    sub.add_parser("demo", help="Launch the interactive Streamlit demo app")

    advise = sub.add_parser("advise", help="Evaluate a junction's traffic under the candidate controllers and recommend one")
    src = advise.add_mutually_exclusive_group(required=True)
    src.add_argument("--spec", help="Junction spec YAML (runs intake first)")
    src.add_argument("--scenario", help="An existing scenario YAML")
    advise.add_argument("--config", default="configs/dqn_v_dqfd.yaml")
    advise.add_argument("--episodes", type=int, default=100, help="Episodes per controller (default 100; under 30 is preliminary)")
    advise.add_argument("--seed-base", type=int, default=30000)
    advise.add_argument("--dqn", action="append", default=[], metavar="[LABEL=]CHECKPOINT[@CONFIG]",
                        help="A DQN trained for THIS junction's demand, as another candidate (label must start with 'dqn')")
    advise.add_argument("--out-dir", default="advice", help="Where advice.json and the comparison files go")

    rep = sub.add_parser("report", help="Render the client report (HTML) from an advice.json")
    rep.add_argument("--advice", required=True)
    rep.add_argument("--out", default="report.html")

    intake = sub.add_parser("intake", help="Turn a junction spec (traffic counts, vehicle mix, turns) into a runnable scenario")
    intake.add_argument("--spec", required=True, help="Junction spec YAML (see configs/examples/junction_example.yaml)")
    intake.add_argument("--out-dir", help="Where the scenario goes (default: projects/<name>)")

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

    from traffic_drl.agent import DQNAgent, QTableAgent, maybe_pretrain, train_agent
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
        pretrained = args.agent == "dqn" and args.env != "toy" and maybe_pretrain(env, agent, config, verbose=True)
        train_agent(env, agent, episodes, max_steps=params.get("max_steps"), log_path=log_path,
                    eval_every=eval_every, eval_episodes=params.get("eval_episodes", 2), best_path=best_path,
                    history=history, eval_at_start=pretrained)
    finally:
        env.close()
    if best_path:
        print(f"best checkpoint: {best_path} (episode {history['best_episode']})")

    ckpt_path = os.path.join(args.out_dir, ckpt_name)
    agent.save(ckpt_path)
    plot_path = plot_reward_curve(log_path, os.path.join(args.out_dir, f"{args.agent}_reward_curve.png"))
    print(f"saved checkpoint={ckpt_path} log={log_path} plot={plot_path}")
    return 0


# The density rule tuned on selection seeds (results_tune_actuated); the same settings every comparison uses.
ACTUATED_DEFAULTS = {"min_green": 10.0, "max_green": 40.0, "ratio": 4.0, "gap_queue": 0.0}


def _run(args) -> int:
    from traffic_drl.agent import DQNAgent
    from traffic_drl.baseline import FixedTimeAgent
    from traffic_drl.config import load_config
    from traffic_drl.env import TraciEnv
    from traffic_drl.live import stream_run

    config = load_config(args.config)
    env = TraciEnv(args.config, scenario=args.scenario, seed=args.seed)
    try:
        if args.controller == "fixed":
            agent = FixedTimeAgent(green_steps=max(1, round(args.green / env.decision_interval)))
        elif args.controller == "actuated":
            from traffic_drl.baseline import DensityActuatedAgent

            agent = DensityActuatedAgent.from_config(config, **ACTUATED_DEFAULTS).attach(env)
        else:
            agent = DQNAgent.from_config(config, state_dim=env.state_size)
            try:
                agent.load(args.checkpoint)
            except (OSError, ValueError) as e:
                raise SystemExit(f"cannot load checkpoint {args.checkpoint}: {e}")
        name = env.scenario_names[0] if env.scenario_names else "default demand"
        stream_run(env, agent, args.out, args.controller, name, delay=args.delay)
    finally:
        env.close()
    return 0


def _save_results_csv(results: list, path: str) -> None:
    import csv
    import os

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["episode", *results[0].keys()])
        for i, r in enumerate(results, start=1):
            writer.writerow([i, *r.values()])
    print(f"wrote {path}")


def _plot(args) -> int:
    from traffic_drl import viz

    if args.plot_kind == "training":
        print("wrote", viz.plot_training(args.log, args.out, evals_path=args.evals, title=args.title))
        return 0

    results = {}
    for item in args.item:
        try:
            key, path = item.rsplit("=", 1)
            scenario, label = key.split(":", 1)
        except ValueError:
            raise SystemExit(f"bad --item {item!r}; expected SCENARIO:LABEL=CSV")
        results.setdefault(scenario, {})[label] = viz.read_csv(path)
    metrics = tuple(args.metrics.split(",")) if args.metrics else viz.plots.COMPARE_DEFAULT
    print(viz.comparison_table(results, metrics))
    print("wrote", viz.plot_comparison(results, args.out, metrics=metrics, title=args.title))
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
    if args.save_csv and len(table) > 1:
        raise SystemExit("--save-csv works with a single checkpoint, not a folder")
    if len(table) == 1:
        path, results, mean = table[0]
        if args.save_csv:
            _save_results_csv(results, args.save_csv)
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
    if args.save_csv:
        _save_results_csv(results, args.save_csv)
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
                            eval_every=config.get("dqn", {}).get("eval_every"),
                            eval_episodes=sw.get("eval_episodes", 2))
    finally:
        env.close()

    print("\nranked settings (best first):")
    for i, row in enumerate(summary, start=1):
        print(f"{i}. " + "  ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))
    print(f"\nwrote {args.out_dir}/sweep_summary.csv, sweep_runs.csv, runs/")
    return 0


def _compare(args) -> int:
    from traffic_drl.compare import run_comparison

    scenarios = [x.strip() for x in args.scenarios.split(",") if x.strip()]
    summary, table = run_comparison(args.config, scenarios, args.controller, episodes=args.episodes,
                                    seed_base=args.seed_base, out_dir=args.out_dir, reference=args.reference,
                                    threshold=args.threshold, min_abs=args.min_abs, metric=args.metric, log=print)
    print()
    print(table)
    print(f"wrote {args.out_dir}/compare_summary.md, compare_summary.csv, compare_episodes.csv")
    return 0


def _intake(args) -> int:
    from traffic_drl import intake

    try:
        result = intake.build_from_file(args.spec, args.out_dir)
    except (intake.SpecError, OSError) as e:
        print(f"intake: {e}", file=sys.stderr)
        return 2
    s = result["summary"]
    print(f"wrote {result['scenario_yaml']} and {result['route_file']}")
    print(f"demand: {s['vehicles']:.0f} vehicles over {s['minutes']:.0f} minutes, peak load {s['peak_load']:.2f} "
          "(1.0 = what one lane per road can discharge)")
    for note in result["advisories"]:
        print(f"note: {note}")
    print(f"next: traffic-drl compare --config configs/dqn_v_dqfd.yaml --scenarios {result['scenario_yaml']} "
          "--controller fixed --controller \"rule=actuated:min=10,max=40,ratio=4,gap=0\" --reference rule")
    return 0


def _advise(args) -> int:
    from traffic_drl import advisor, intake

    notes, scenario, context = [], args.scenario, None
    if args.spec:
        try:
            built = intake.build_from_file(args.spec, os.path.join(args.out_dir, "scenario"))
        except (intake.SpecError, OSError) as e:
            print(f"advise: {e}", file=sys.stderr)
            return 2
        scenario, notes, context = built["scenario_yaml"], built["advisories"], built["context"]
    dqn = {}
    for item in args.dqn:
        label, _, ckpt = item.partition("=") if "=" in item.split("@")[0] else ("dqn", "", item)
        dqn[label] = ckpt
    advice = advisor.advise(scenario, args.out_dir, config=args.config, episodes=args.episodes,
                            seed_base=args.seed_base, dqn=dqn, load_notes=notes, context=context)
    from traffic_drl import report

    report_path = report.write_report(advice, os.path.join(args.out_dir, "report.html"))
    print()
    print(advice["table_markdown"])
    print(advice["headline"])
    for r in advice["reasons"]:
        print(f"- {r}")
    print("Settings:", json.dumps(advice["settings"], indent=2))
    for c in advice["caveats"]:
        print(f"note: {c}")
    print(f"wrote {args.out_dir}/advice.json and {report_path} (open in a browser; print to PDF to share)")
    return 0


def _report(args) -> int:
    from traffic_drl import report

    with open(args.advice) as f:
        advice = json.load(f)
    print(f"wrote {report.write_report(advice, args.out)}")
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
    elif args.command == "run":
        return _run(args)
    elif args.command == "plot":
        return _plot(args)
    elif args.command == "baseline":
        return _baseline(args)
    elif args.command == "sweep":
        return _sweep(args)
    elif args.command == "evaluate":
        return _evaluate(args)
    elif args.command == "compare":
        return _compare(args)
    elif args.command == "intake":
        return _intake(args)
    elif args.command == "advise":
        return _advise(args)
    elif args.command == "report":
        return _report(args)
    elif args.command == "demo":
        import subprocess
        from pathlib import Path

        app = Path(__file__).with_name("app.py")
        return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)],
                               cwd=str(Path(__file__).resolve().parents[1]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
