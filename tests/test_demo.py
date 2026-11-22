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


def test_every_demo_controller_is_accepted_by_the_real_run_parser():
    """The fake simulator accepts any name; the real `traffic-drl run` parser does not."""
    for key in core.KEYS:
        cmd = core.build_run_command(key, "configs/scenarios/tidal.yaml", "models/dqfd_tidal_s3.npz", 1, 0, "o.jsonl")
        args = cli.build_parser().parse_args(cmd[cmd.index("run"):])
        assert args.command == "run" and args.controller == core.CLI_CONTROLLER[key]


def test_run_command_streams_a_density_rule_episode():
    traci_env.traci = FakeTraci()
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "r.jsonl")
        code = cli.main(["run", "--controller", "actuated", "--config", os.path.join(ROOT, "configs", "dqn_v_dqfd.yaml"),
                         "--scenario", os.path.join(ROOT, "configs", "scenarios", "tidal.yaml"), "--seed", "40000", "--out", out])
        evs = _events(out)
    assert code == 0 and evs[0]["controller"] == "actuated" and evs[-1]["event"] == "done"


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
    assert "--checkpoint" not in core.build_run_command("rule", "s.yaml", "c.npz", 1, 0, "o")
    assert "checkpoints/dqn_final.npz".replace("/", os.sep) in core.list_checkpoints()
    assert "models/dqfd_tidal_s3.npz".replace("/", os.sep) in core.list_checkpoints()
    text = core.final_results_markdown()
    assert "| tidal |" in text and "| grid_d800_r4 |" in text and "reference rule" in text
    assert "GREEN" in app.signal_html(0) and "RED" in app.signal_html(0)
    assert app.queue_bars_html(["east", "north"], [3, 99]).count("width:100%") == 1   # capped at the scale


def test_best_checkpoint_is_chosen_per_scenario():
    tidal, rush = "configs/scenarios/tidal.yaml", "configs/scenarios/rush_hour.yaml"
    assert core.resolve_checkpoint(core.AUTO, tidal) == "models/dqfd_tidal_s3.npz"
    assert core.resolve_checkpoint(core.AUTO, rush) == "models/dqfd_rush_s2.npz"
    assert core.resolve_checkpoint(core.AUTO, "configs/scenarios/low_traffic.yaml") == "checkpoints/dqn_mixed.npz"
    assert core.resolve_checkpoint("checkpoints/dqn_final.npz", rush) == "checkpoints/dqn_final.npz"   # explicit choice wins


def test_every_scenario_has_an_existing_scenario_file_and_agent_with_the_right_config():
    import json

    manifest = json.load(open(os.path.join(ROOT, "models", "manifest.json")))
    defaults = {info["default"] for info in manifest["models"].values()}
    for label, yaml_path in core.SCENARIOS.items():
        assert os.path.exists(os.path.join(ROOT, yaml_path)), label
        ckpt, _ = core.BEST_CHECKPOINT[yaml_path]
        assert os.path.exists(os.path.join(ROOT, ckpt)), ckpt
        assert (ckpt in defaults) or ckpt.startswith("checkpoints/"), f"{ckpt} is not the manifest's default"
        assert core.config_for(ckpt) == ("configs/dqn_v_dqfd.yaml" if ckpt.startswith("models/") else "configs/dqn.yaml")
    assert core.build_run_command("dqn", "s.yaml", "models/gen_s3.npz", 1, 0, "o")[6:8] == ["--config", "configs/dqn_v_dqfd.yaml"]


def test_the_final_agents_load_with_the_final_config_and_act():
    import numpy as np
    from traffic_drl.agent import DQNAgent
    from traffic_drl.config import load_config

    cfg = load_config(os.path.join(ROOT, core.NEW_CONFIG))
    traci_env.traci = FakeTraci()
    env = traci_env.TraciEnv(os.path.join(ROOT, core.NEW_CONFIG))
    agent = DQNAgent.from_config(cfg, state_dim=env.state_size)
    agent.load(os.path.join(ROOT, "models", "dqfd_rush_s2.npz"))
    assert agent.act(np.zeros(env.state_size, dtype=np.float32), greedy=True) in (0, 1)


def test_verdict_against_the_rule_is_cautious():
    mk = lambda w: {"mean_total_waiting": w, "throughput_per_hour": 2000.0}
    assert "about level" in core.verdict_vs_rule(mk(100.0), mk(103.0))
    assert "about level" in core.verdict_vs_rule(mk(0.2), mk(1.5))          # under 2 vehicles: a tie
    assert "fewer vehicles waiting than the density rule" in core.verdict_vs_rule(mk(100.0), mk(80.0))
    assert "density rule did better" in core.verdict_vs_rule(mk(100.0), mk(120.0))


def test_chart_lines_are_joined_when_controllers_report_at_different_times():
    import pandas as pd
    a = pd.Series([1.0, 3.0, 5.0], index=[0.0, 0.2, 0.4])
    b = pd.Series([2.0, 4.0], index=[0.1, 0.3])
    df = core.align_series({"a": a, "b": b})
    assert list(df.index) == [0.0, 0.1, 0.2, 0.3, 0.4]
    assert df["a"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]       # filled between its own points
    assert df["b"].isna().tolist() == [True, False, False, False, True]   # not extended past its range


def _app_test():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(os.path.join(ROOT, "traffic_drl", "app.py"), default_timeout=90)


def test_app_renders_without_running_anything():
    at = _app_test().run()
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs] == ["Live demo", "Test results", "How it works"]
    assert at.sidebar.button[0].label == "Run all three controllers" and not at.sidebar.button[0].disabled
    assert len(at.sidebar.selectbox[0].options) == 10 and at.sidebar.selectbox[0].options[0] == core.CUSTOM
    assert any("grid_d800_r4" in str(m.value) for m in at.markdown)       # the consolidated results table is on the page


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
    assert all(data[k][-1]["event"] == "done" for k in ("fixed", "rule", "dqn"))
    assert any("fewer vehicles waiting" in str(i.value) and "density rule" in str(i.value) for i in at.info)   # both verdicts shown
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


def test_custom_traffic_builds_a_runnable_scenario(tmp_path):
    rates = {"east": 300, "north": 600, "west": 300, "south": 600}
    built = core.build_custom(core.custom_spec("my_junction", rates, 30, False,
                                               {"motorcycle": 62, "car": 22, "bus": 8, "goods": 8}, {"left": 10, "right": 10}),
                              str(tmp_path))
    assert os.path.exists(built["scenario_yaml"]) and built["summary"]["minutes"] == 30
    # an unknown scenario gets the generalist, not a model trained for other traffic
    assert core.resolve_checkpoint(core.AUTO, built["scenario_yaml"]) == core.GENERALIST


def test_custom_tidal_swap_makes_two_periods_and_all_zero_mix_means_cars(tmp_path):
    spec = core.custom_spec("t", {"east": 200, "north": 800, "west": 200, "south": 800}, 20, True, {"car": 0}, {})
    assert [p["minutes"] for p in spec["demand"]] == [10, 10]
    assert spec["demand"][1]["east"] == 800 and spec["demand"][1]["north"] == 200       # axes trade rates
    assert spec["vehicle_mix"] == "cars"
    assert core.custom_spec("t", {"east": 1, "north": 1, "west": 1, "south": 1}, 99)["duration_minutes"] == 30   # capped at the episode length


def test_app_custom_mode_shows_controls_and_load():
    at = _app_test().run()
    assert not at.exception, [e.value for e in at.exception]
    by_label = {n.label: n for n in at.sidebar.number_input}
    assert {"North (veh/h)", "East (veh/h)", "South (veh/h)", "West (veh/h)"} <= set(by_label)
    assert any(m.label == "Junction load" for m in at.sidebar.metric)
    assert not at.sidebar.warning
    by_label["North (veh/h)"].set_value(1500).run()                        # 1500/1800 + 400/1800 > 1: over capacity
    assert at.sidebar.warning and not at.exception
