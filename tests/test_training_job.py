"""Training jobs: progress hook, status file, cancel, and one tiny end-to-end job in SUMO."""
import json
import os
import time

import pytest
import yaml

from traffic_drl import intake, training_job
from traffic_drl.agent import DQNAgent, train_agent
from traffic_drl.env import SimpleQueueEnv

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _agent():
    return DQNAgent(state_dim=4, hidden_sizes=(8,), batch_size=8, learn_start=8, buffer_size=200, seed=0)


def test_on_episode_reports_every_episode_and_can_stop_early():
    seen = []

    def hook(info):
        seen.append(info["episode"])
        return info["episode"] >= 3

    rewards = train_agent(SimpleQueueEnv(seed=0, state_scale=20, include_phase=True), _agent(), episodes=10,
                          max_steps=20, verbose=False, on_episode=hook)
    assert seen == [1, 2, 3] and len(rewards) == 3


def test_on_episode_passes_the_periodic_evaluation():
    evals = []
    train_agent(SimpleQueueEnv(seed=0, state_scale=20, include_phase=True), _agent(), episodes=4, max_steps=20,
                verbose=False, eval_every=2, eval_episodes=1, on_episode=lambda i: evals.append(i["eval"]) and False)
    assert [e is not None for e in evals] == [False, True, False, True]    # called every episode; evaluation on 2 and 4


def test_status_roundtrip_and_missing(tmp_path):
    assert training_job.read_status(str(tmp_path))["state"] == "missing"
    st = training_job.Status(str(tmp_path), state="running")
    st.update(episode=3)
    assert training_job.read_status(str(tmp_path))["episode"] == 3
    st.update()
    assert training_job.read_status(str(tmp_path))["state"] == "running"


def test_running_job_that_stops_reporting_is_stalled(tmp_path):
    st = training_job.Status(str(tmp_path), state="running")
    st.update()
    data = json.loads((tmp_path / "status.json").read_text())
    data["updated"] = time.time() - training_job.STALE_AFTER - 5
    (tmp_path / "status.json").write_text(json.dumps(data))
    assert training_job.read_status(str(tmp_path))["state"] == "stalled"


def _scenario(tmp_path):
    spec = {"name": "tj", "demand": {"east": 250, "north": 600, "west": 250, "south": 600}, "duration_minutes": 10}
    return intake.build_scenario(spec, tmp_path / "src")["scenario_yaml"]


def test_snapshot_makes_the_job_self_contained(tmp_path):
    snap = training_job.snapshot_scenario(_scenario(tmp_path), str(tmp_path / "job"))
    assert os.path.exists(tmp_path / "job" / "scenario.rou.xml")
    assert yaml.safe_load(open(snap))["route_file"] == "scenario.rou.xml"


def _fast_config(tmp_path):
    """The shipped recipe with a tiny teacher phase so a job takes seconds, not minutes."""
    cfg = {"extends": os.path.abspath(os.path.join(ROOT, "configs", "dqn_v_dqfd.yaml")),
           "dqn": {"eval_every": 1, "eval_episodes": 1, "learn_start": 50,
                   "pretrain": {"teacher": {"min": 10, "max": 40, "ratio": 4, "gap": 0}, "episodes": 1, "noise": 0.2,
                                "offline_steps": 20, "epsilon_after": 0.1}}}
    path = tmp_path / "fast.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return str(path)


def test_cancel_before_start_writes_no_model(tmp_path):
    pytest.importorskip("traci")
    job = tmp_path / "job"
    snap = training_job.snapshot_scenario(_scenario(tmp_path), str(job))
    training_job.request_cancel(str(job))
    result = training_job.run_job(snap, str(job), config_path=_fast_config(tmp_path), episodes=2, seeds=[0])
    assert result == {} and training_job.read_status(str(job))["state"] == "cancelled"
    assert not (job / "model.npz").exists()


def test_tiny_end_to_end_job(tmp_path):
    pytest.importorskip("traci")
    job = tmp_path / "job"
    snap = training_job.snapshot_scenario(_scenario(tmp_path), str(job))
    result = training_job.run_job(snap, str(job), config_path=_fast_config(tmp_path), episodes=2, seeds=[0, 1],
                                  final_eval_episodes=1, log=lambda *_: None)
    assert (job / "model.npz").exists() and result["chosen_seed"] in (0, 1) and len(result["seeds"]) == 2
    assert set(result["reference_waiting"]) == {"fixed", "rule"} and "not a test result" in result["note"]
    status = training_job.read_status(str(job))
    assert status["state"] == "done" and status["episode"] == 2 and len(status["rewards"]) == 2
    # the chosen model loads and runs under the same config the app will use
    from traffic_drl import compare
    from traffic_drl.env import TraciEnv

    env = TraciEnv(os.path.join(ROOT, "configs", "dqn_v_dqfd.yaml"), scenario=snap)
    try:
        agent = compare.build_agent("dqn", result["model"], __import__("traffic_drl.config", fromlist=["x"]).load_config(
            os.path.join(ROOT, "configs", "dqn_v_dqfd.yaml")), env)
        env.reset()
        assert agent.act(env._get_state(), greedy=True) in (0, 1)
    finally:
        env.close()
