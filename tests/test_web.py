"""The web API: validation, scenario building, agents, live comparison (fake simulator), evaluation errors, training jobs."""
import json
import os
import sys
import time

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from traffic_drl import demo_core as core  # noqa: E402
from traffic_drl import training_job as tj  # noqa: E402
from traffic_drl.web.server import create_app  # noqa: E402

HERE = os.path.dirname(__file__)
FAKE_RUN = os.path.join(HERE, "fake_run.py")
TRAFFIC = {"rates": {"east": 300, "north": 600, "west": 300, "south": 600}, "minutes": 30,
           "mix_pct": {"motorcycle": 62, "car": 22, "bus": 8, "goods": 8}, "turns_pct": {"left": 10, "right": 10}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAFFIC_DRL_HOME", str(tmp_path))
    with TestClient(create_app()) as c:
        yield c


def test_index_and_static_files_are_served(client):
    page = client.get("/")
    assert page.status_code == 200 and "Signal Studio" in page.text
    assert client.get("/static/app.js").status_code == 200 and client.get("/static/app.css").status_code == 200


def test_preview_reports_load_and_rejects_bad_traffic(client):
    ok = client.post("/api/preview", json=TRAFFIC).json()
    assert ok["summary"]["vehicles"] == pytest.approx(900) and ok["advisories"] == []
    over = client.post("/api/preview", json={**TRAFFIC, "rates": {"east": 1500, "north": 1500, "west": 1500, "south": 1500}}).json()
    assert over["summary"]["peak_load"] > 1 and over["advisories"]
    bad = client.post("/api/preview", json={**TRAFFIC, "rates": {"east": 99999}})
    assert bad.status_code == 422 and "outside" in bad.json()["error"]


def test_scenario_is_built_and_saved(client, tmp_path):
    made = client.post("/api/scenario", json=TRAFFIC).json()
    d = tmp_path / "web" / "scenarios" / made["id"]
    assert (d / "my_junction.yaml").exists() and (d / "spec.yaml").exists() and made["summary"]["minutes"] == 30


def test_ids_are_validated_and_unknown_things_404(client):
    assert client.get("/api/compare/..%2Fetc").status_code in (400, 404)
    assert client.get("/api/compare/nope").status_code == 404
    assert client.get("/api/evaluate/nope").status_code == 404
    assert client.get("/api/train/nope").status_code == 404
    assert client.post("/api/compare", json={"scenario_id": "nope"}).status_code == 404
    assert client.post("/api/evaluate", json={"scenario_id": "bad id!"}).status_code == 400


def test_agents_listed_without_paths(client):
    agents = client.get("/api/agents").json()["agents"]
    assert any(a["id"] == "generalist" for a in agents) and all("path" not in a for a in agents)


def test_live_comparison_streams_events_from_the_three_controllers(client, monkeypatch):
    def fake_command(controller, scenario_yaml, checkpoint, seed, delay, out_path):
        return [sys.executable, FAKE_RUN, "--out", out_path, "--controller", controller]

    monkeypatch.setattr(core, "build_run_command", fake_command)
    sid = client.post("/api/scenario", json=TRAFFIC).json()["id"]
    run = client.post("/api/compare", json={"scenario_id": sid, "agent_id": "generalist", "speed": "fast"}).json()
    counts, seen, last = {"fixed": 0, "rule": 0, "dqn": 0}, {"fixed": [], "rule": [], "dqn": []}, None
    for _ in range(100):
        last = client.get(f"/api/compare/{run['id']}", params=counts).json()
        for k in counts:
            seen[k] += last["events"][k]
            counts[k] = last["counts"][k]
        if last["done"] or last["failed"]:
            break
        time.sleep(0.1)
    assert last["done"] and not last["failed"]
    assert all(seen[k][0]["event"] == "start" and seen[k][-1]["event"] == "done" for k in seen)
    assert all(len(seen[k]) == counts[k] for k in seen)            # incremental polling returned every event exactly once


def test_comparison_failure_is_reported_not_hidden(client, monkeypatch):
    monkeypatch.setattr(core, "build_run_command", lambda c, s, k, seed, d, out: [sys.executable, FAKE_RUN, "--out", out, "--controller", c, "--fail"])
    sid = client.post("/api/scenario", json=TRAFFIC).json()["id"]
    run = client.post("/api/compare", json={"scenario_id": sid}).json()
    for _ in range(100):
        r = client.get(f"/api/compare/{run['id']}").json()
        if r["failed"]:
            break
        time.sleep(0.1)
    assert r["failed"] and not r["done"]


def test_training_job_status_result_and_cancel(client, tmp_path):
    job = tmp_path / "jobs" / "my_junction_20260101_000000"
    job.mkdir(parents=True)
    tj.Status(str(job), state="running", episodes=10, seeds=[0], episode=4).update()
    r = client.get(f"/api/train/{job.name}").json()
    assert r["status"]["state"] == "running" and "result" not in r
    assert client.post(f"/api/train/{job.name}/cancel").json()["ok"] and (job / "cancel").exists()
    tj.Status(str(job), state="done", episodes=10, seeds=[0]).update()
    (job / "model.npz").write_bytes(b"x")
    (job / "result.json").write_text(json.dumps({"model": str(job / "model.npz"), "chosen_seed": 0}))
    done = client.get(f"/api/train/{job.name}").json()
    assert done["agent_id"] == f"job:{job.name}" and done["result"]["chosen_seed"] == 0
    # a finished job's agent is offered in the agent list
    assert any(a["id"] == f"job:{job.name}" for a in client.get("/api/agents").json()["agents"])
