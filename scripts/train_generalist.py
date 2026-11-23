#!/usr/bin/env python3
"""Train one generalist DQN on the client-style traffic pool, for one seed and one network size.

    python scripts/train_generalist.py --seed 0 --out-dir runs/gen2/h64_s0 --hidden 64 --episodes 300

Recipe: the shipped one (configs/dqn_v_dqfd.yaml: learning from the density rule's demonstrations, frozen buffer,
margin loss), trained on configs/scenarios/client_pool/train. Checkpoints are chosen on the separate `select` pool
(never the test pool), the chosen one is re-scored on different selection seeds, and the density rule and the fixed
timer are scored on exactly the same select scenarios and seeds, so the result file says how the agent stands
against them before any test seed is touched.
"""
import argparse
import copy
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from traffic_drl import compare  # noqa: E402
from traffic_drl.agent import DQNAgent, evaluate, maybe_pretrain, train_agent  # noqa: E402
from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import TraciEnv  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RANKING_SEED_BASE = 20_000


def score_on_select(make_env, agent_or_none, cfg, kind=None, arg=None, episodes=2, seed_base=10_000):
    """Score a controller on the select pool on a FRESH environment, so every controller sees identical traffic
    (the environment's seed counter restarts at `seed_base`)."""
    env = make_env()
    try:
        agent = agent_or_none if agent_or_none is not None else compare.build_agent(kind, arg, cfg, env)
        if hasattr(agent, "reset"):
            agent.reset()
        return evaluate(env, agent, episodes, seed_base=seed_base)
    finally:
        env.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--hidden", type=int, default=64, help="Width of both hidden layers")
    ap.add_argument("--episodes", type=int, default=300)
    ap.add_argument("--chunk", type=int, default=30, help="Episodes between selection evaluations")
    ap.add_argument("--config", default=os.path.join(ROOT, "configs", "dqn_v_dqfd.yaml"))
    ap.add_argument("--pool", default=os.path.join(ROOT, "configs", "scenarios", "client_pool"))
    ap.add_argument("--pretrain-episodes", type=int, default=60)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    train_paths = sorted(glob.glob(os.path.join(args.pool, "train", "train_*.yaml")))
    select_paths = sorted(glob.glob(os.path.join(args.pool, "select", "sel*_*.yaml")))
    assert train_paths and select_paths, "run scripts/make_client_pool.py first"

    cfg = copy.deepcopy(load_config(args.config))
    d = cfg["dqn"]
    d.update(seed=args.seed, hidden_sizes=[args.hidden, args.hidden], buffer_size=40000, gamma=0.99, double_dqn=True,
             epsilon_decay=0.985, lr_decay=0.992)
    d["pretrain"] = {**d["pretrain"], "episodes": args.pretrain_episodes, "offline_steps": 6000, "epsilon_after": 0.15}

    env = TraciEnv(args.config, scenario=train_paths)
    make_sel_env = lambda: TraciEnv(args.config, scenario=select_paths)   # noqa: E731
    agent = DQNAgent.from_config(cfg, state_dim=env.state_size)
    best_path = os.path.join(args.out_dir, "best.npz")
    started = time.time()
    log = open(os.path.join(args.out_dir, "progress.log"), "w", buffering=1)

    def say(msg):
        log.write(f"[{time.time() - started:6.0f}s] {msg}\n")

    try:
        say("pretraining from the density rule's demonstrations")
        maybe_pretrain(env, agent, cfg)
        def score():
            env.close()              # TraCI allows one live connection; the next training episode reconnects by itself
            return score_on_select(make_sel_env, agent, cfg)["mean_total_waiting"]    # 2 episodes per select scenario

        best, best_ep, evals = score(), 0, [{"episode": 0, "waiting": None}]
        evals[0]["waiting"] = best
        agent.save(best_path)
        say(f"after demonstrations: select waiting {best:.2f}")
        rewards = []
        for done in range(0, args.episodes, args.chunk):
            n = min(args.chunk, args.episodes - done)
            rewards += train_agent(env, agent, n, verbose=False)
            s = score()
            evals.append({"episode": done + n, "waiting": s})
            if s < best:
                best, best_ep = s, done + n
                agent.save(best_path)
            say(f"episode {done + n}: select waiting {s:.2f} (best {best:.2f} at episode {best_ep})")
        agent.load(best_path)
        env.close()
        final = score_on_select(make_sel_env, agent, cfg, episodes=3, seed_base=RANKING_SEED_BASE)
        refs = {"rule": score_on_select(make_sel_env, None, cfg, "actuated", "min=10,max=40,ratio=4,gap=0", 3, RANKING_SEED_BASE),
                "fixed": score_on_select(make_sel_env, None, cfg, "fixed", "40", 3, RANKING_SEED_BASE)}
        result = {"seed": args.seed, "hidden": args.hidden, "episodes": args.episodes, "best_episode": best_ep,
                  "final_select_waiting": final["mean_total_waiting"],
                  "rule_select_waiting": refs["rule"]["mean_total_waiting"],
                  "fixed_select_waiting": refs["fixed"]["mean_total_waiting"],
                  "per_scenario": {k: v for k, v in final.items() if k.endswith("/mean_total_waiting")},
                  "per_scenario_rule": {k: v for k, v in refs["rule"].items() if k.endswith("/mean_total_waiting")},
                  "evals": evals, "seconds": time.time() - started}
        with open(os.path.join(args.out_dir, "result.json"), "w") as f:
            json.dump(result, f, indent=1)
        say(f"done: select waiting {final['mean_total_waiting']:.2f} vs rule {refs['rule']['mean_total_waiting']:.2f} "
            f"vs fixed {refs['fixed']['mean_total_waiting']:.2f}")
    finally:
        env.close()


if __name__ == "__main__":
    main()
