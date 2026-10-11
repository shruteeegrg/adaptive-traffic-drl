"""Demo tests: JSON-lines streaming, the run command, helpers, and the
Streamlit app itself driven headlessly (no SUMO, no browser)."""

import json
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl import app, cli, demo_core as core  # noqa: E402
from traffic_drl.baseline import FixedTimeAgent  # noqa: E402
from traffic_drl.env import traci_env  # noqa: E402
from traffic_drl.live import stream_run  # noqa: E402
from test_state_reward import FakeTraci  # noqa: E402

FAKE_RUN = os.path.join(os.path.dirname(__file__), "fake_run.py")


def _events(path):
    return [json.loads(line) for line in open(path)]


def test_stream_run_writes_start_steps_done():
    traci_env.traci = FakeTraci()
    env = traci_env.TraciEnv(os.path.join(ROOT, "configs", "dqn.yaml"))
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "x.jsonl")
        final = stream_run(env, FixedTimeAgent(8), out, "fixed", "tidal")
        evs = _events(out)
    assert evs[0]["event"] == "start" and evs[0]["approaches"] == ["east", "north", "west", "south"]
    assert evs[-1]["event"] == "done" and evs[-1]["t"] == final["t"] >= 1800.0
    assert all(e["event"] == "step" for e in evs[1:-1]) and len(evs) > 50
    for key in ("queues", "backlog", "waiting", "green", "mean_total_waiting", "throughput_per_hour", "switches"):
        assert key in evs[-1]
    assert evs[-1]["waiting"] == sum(evs[-1]["queues"]) + evs[-1]["backlog"]


def test_run_command_streams_a_fixed_time_episode():
    traci_env.traci = FakeTraci()
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "r.jsonl")
        code = cli.main(["run", "--controller", "fixed", "--config", os.path.join(ROOT, "configs", "dqn.yaml"),
                         "--scenario", os.path.join(ROOT, "configs", "scenarios", "rush_hour.yaml"),
                         "--seed", "40000", "--out", out])
        evs = _events(out)
    assert code == 0 and evs[0]["scenario"] == "rush_hour" and evs[-1]["event"] == "done"


def test_run_command_with_the_shipped_checkpoint():
    traci_env.traci = FakeTraci()
    ckpt = os.path.join(ROOT, "checkpoints", "dqn_final.npz")
    assert os.path.exists(ckpt)
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "r.jsonl")
        code = cli.main(["run", "--controller", "dqn", "--checkpoint", ckpt, "--out", out,
                         "--config", os.path.join(ROOT, "configs", "dqn.yaml")])
        assert code == 0 and _events(out)[-1]["event"] == "done"
        try:
            cli.main(["run", "--controller", "dqn", "--checkpoint", os.path.join(d, "nope.npz"), "--out", out,
                      "--config", os.path.join(ROOT, "configs", "dqn.yaml")])
        except SystemExit as e:
            assert "cannot load checkpoint" in str(e)
        else:
            raise AssertionError("expected SystemExit")


def test_read_new_events_leaves_a_half_written_line_for_next_time():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.jsonl")
        assert core.read_new_events(p, 0) == ([], 0)                       # no file yet
        open(p, "w").write('{"a": 1}\n{"b": ')
        evs, off = core.read_new_events(p, 0)
        assert evs == [{"a": 1}]
        open(p, "a").write('2}\n')
        evs, off = core.read_new_events(p, off)
        assert evs == [{"b": 2}] and core.read_new_events(p, off) == ([], off)


def test_verdict_wording_is_honest_in_all_directions():
    mk = lambda w, t=2000.0: {"mean_total_waiting": w, "throughput_per_hour": t}
    assert "fewer vehicles waiting" in core.verdict(mk(115.0, 2445), mk(9.9, 2749)) and "91%" in core.verdict(mk(115.0), mk(9.9))
    assert "fixed timer did better" in core.verdict(mk(139.7), mk(198.5))
    assert "About the same" in core.verdict(mk(100.0), mk(102.0))
    assert "nothing to separate" in core.verdict(mk(0.1), mk(0.2))


def test_helpers_and_results_table():
    cmd = core.build_run_command("dqn", "configs/scenarios/tidal.yaml", "checkpoints/dqn_final.npz", 7, 0.05, "o.jsonl")
    assert cmd[1:4] == ["-m", "traffic_drl.cli", "run"] and "--checkpoint" in cmd and cmd[cmd.index("--seed") + 1] == "7"
    assert "--checkpoint" not in core.build_run_command("fixed", "s.yaml", "c.npz", 1, 0, "o")
    assert "checkpoints/dqn_final.npz".replace("/", os.sep) in core.list_checkpoints()
    rows = core.results_table()
    assert {r["Scenario"] for r in rows} == {"Tidal", "Rush hour", "Low traffic"}
    tidal = next(r for r in rows if r["Scenario"] == "Tidal")
    assert tidal["Waiting, DQN"] < tidal["Waiting, fixed-time"] / 5
    assert "GREEN" in app.signal_html(0) and "RED" in app.signal_html(0)
    assert app.queue_bars_html(["east", "north"], [3, 99]).count("width:100%") == 1   # capped at the scale


def _app_test():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(os.path.join(ROOT, "traffic_drl", "app.py"), default_timeout=90)


def test_app_renders_without_running_anything():
    at = _app_test().run()
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs] == ["Live demo", "Test results", "How it works"]
    assert at.sidebar.button[0].label == "Run both controllers" and not at.sidebar.button[0].disabled
    assert len(at.sidebar.selectbox[0].options) == 3
    assert any("Tidal" in str(df.value) for df in at.dataframe)           # results table is on the page


def _fake_builder(fail=False):
    def build(controller, scenario_yaml, checkpoint, seed, delay, out_path):
        cmd = [sys.executable, FAKE_RUN, "--out", out_path, "--controller", controller]
        return cmd + (["--fail"] if fail else [])
    return build


def test_app_live_run_with_fake_simulator_end_to_end():
    real = core.build_run_command
    core.build_run_command = _fake_builder()
    try:
        at = _app_test().run()
        at.sidebar.button[0].click().run()
    finally:
        core.build_run_command = real
    assert not at.exception, [e.value for e in at.exception]
    data = at.session_state["last_run"]["data"]
    assert data["fixed"][-1]["event"] == "done" and data["dqn"][-1]["event"] == "done"
    assert any("fewer vehicles waiting" in str(i.value) for i in at.info)   # verdict shown
    assert not at.error


def test_app_shows_a_helpful_error_when_the_simulator_cannot_start():
    real = core.build_run_command
    core.build_run_command = _fake_builder(fail=True)
    try:
        at = _app_test().run()
        at.sidebar.button[0].click().run()
    finally:
        core.build_run_command = real
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.error) == 1 and "Test results" in str(at.error[0].value) and "sumo" in str(at.error[0].value)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)


def test_junction_drawing_shows_queues_and_signal():
    from traffic_drl import app
    names = ["east", "north", "west", "south"]
    svg = app.junction_html(names, [3, 0, 99, 1], green=0)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert svg.count('fill="#2a78d6"') == 3 + 0 + 12 + 1          # one square per queued car, capped at 12
    assert svg.count("#1e9e5a") == 2 and svg.count("#c0392b") == 2  # north-south green, east-west red
    assert "East: 3" in svg and "West: 99" in svg
