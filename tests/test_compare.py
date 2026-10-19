"""Statistics, the density-responsive baseline, Double DQN and the `compare` command.
No SUMO needed (a fake traci stands in).
    python -m pytest tests/test_compare.py -v     (or: python tests/test_compare.py)
"""

import csv
import math
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from traffic_drl import stats  # noqa: E402
from traffic_drl.agent import DQNAgent  # noqa: E402
from traffic_drl.baseline import DensityActuatedAgent  # noqa: E402
from traffic_drl.compare import parse_controller, run_comparison, verdict  # noqa: E402
from traffic_drl.config import load_config  # noqa: E402
from traffic_drl.env import traci_env  # noqa: E402
from test_state_reward import FakeTraci  # noqa: E402

CFG = os.path.join(ROOT, "configs", "dqn.yaml")


# ------------------------------------------------------------------ statistics
def test_t_distribution_matches_textbook_values():
    assert math.isclose(stats.t_two_sided_p(2.228, 10), 0.05, abs_tol=2e-4)       # t critical, df = 10
    assert math.isclose(stats.t_two_sided_p(2.086, 20), 0.05, abs_tol=2e-4)
    assert math.isclose(stats.t_two_sided_p(1.96, 100000), 0.05, abs_tol=2e-4)    # approaches the normal
    assert stats.t_two_sided_p(0.0, 5) == 1.0
    assert math.isclose(stats.t_critical(10), 2.228, abs_tol=2e-3)
    assert math.isclose(stats.t_critical(99), 1.984, abs_tol=2e-3)


def _p_by_integration(t, df, upper=200.0, steps=200000):
    """Independent check of the p-value: integrate the Student t density numerically (Simpson)."""
    c = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)
    pdf = lambda x: c * (1 + x * x / df) ** (-(df + 1) / 2)   # noqa: E731
    h = (upper - abs(t)) / steps
    total = pdf(abs(t)) + pdf(upper)
    for i in range(1, steps):
        total += pdf(abs(t) + i * h) * (4 if i % 2 else 2)
    return 2 * total * h / 3


def test_p_value_matches_numerical_integration_of_the_t_density():
    for t, df in ((0.35, 15.8), (1.7, 9.2), (2.5, 27.9), (4.0, 5.0), (3.1, 99.0)):
        assert math.isclose(stats.t_two_sided_p(t, df), _p_by_integration(t, df), rel_tol=2e-3, abs_tol=2e-5), (t, df)


def test_welch_statistic_and_degrees_of_freedom():
    a, b = [10.0, 12.0, 11.0, 13.0, 9.0], [14.0, 15.0, 13.0, 16.0, 17.0, 15.0]
    r = stats.welch_t_test(a, b)
    va, vb = 2.5 / 5, (sum((x - 15.0) ** 2 for x in b) / 5) / 6
    assert math.isclose(r["t"], (11.0 - 15.0) / math.sqrt(va + vb), rel_tol=1e-12)
    assert math.isclose(r["df"], (va + vb) ** 2 / (va ** 2 / 4 + vb ** 2 / 5), rel_tol=1e-12)
    assert r["diff"] == -4.0 and r["p"] < 0.01


def test_identical_and_clearly_different_samples():
    same = [5.0, 6.0, 7.0, 8.0]
    assert stats.welch_t_test(same, same)["p"] == 1.0
    far = stats.welch_t_test([100, 101, 99, 100.5], [10, 11, 9, 10.5])
    assert far["p"] < 1e-6 and far["t"] > 0
    assert stats.cohens_d([100, 101, 99, 100.5], [10, 11, 9, 10.5]) > 10
    m, half = stats.ci95([10.0, 12.0, 11.0, 13.0, 9.0])
    assert m == 11.0 and math.isclose(half, 2.776 * math.sqrt(2.5 / 5), rel_tol=2e-3)


def test_paired_test_uses_per_episode_differences():
    a = [10, 12, 14, 16, 18, 20]
    b = [9, 11, 13, 15, 17, 19]              # always exactly 1 lower: paired difference has no spread
    assert stats.paired_t_test(a, b)["p"] == 0.0
    assert stats.welch_t_test(a, b)["p"] > 0.3      # the independent test cannot see it


def test_verdict_needs_statistical_and_practical_significance():
    assert verdict(100, 80, 0.001, 0.05, 2) == "better"
    assert verdict(100, 120, 0.001, 0.05, 2) == "worse"
    assert verdict(100, 80, 0.4, 0.05, 2) == "tie"            # not significant
    assert verdict(100, 98.5, 0.001, 0.05, 2) == "small"      # significant but under 5 percent and under 2 vehicles
    assert verdict(1.5, 0.5, 0.001, 0.05, 2) == "small"       # near-zero traffic: a 67 percent change of nothing


# ------------------------------------------------------------------ actuated controller
def _state(queues, phase, elapsed, scale=20.0, wait=(0, 0, 0, 0)):
    s = np.zeros(11, dtype=np.float32)
    s[0:4] = np.asarray(queues, dtype=np.float32) / scale
    s[4:8] = wait
    s[8 + phase] = 1.0
    s[10] = elapsed / 60.0
    return s


def _actuated(**kw):
    return DensityActuatedAgent.from_config(load_config(CFG), **kw)


def test_actuated_reads_the_state_layout_from_the_config():
    a = _actuated()
    assert (a.queue_idx, a.phase_idx, a.elapsed_idx) == (0, 8, 10)
    assert a.ns_cols == [1, 3] and a.ew_cols == [0, 2]           # approaches: east, north, west, south


def test_actuated_respects_minimum_and_maximum_green():
    a = _actuated(min_green=10, max_green=60)
    heavy_other = [8, 0, 8, 0]                                    # east-west heavy while north-south has green
    assert a.act(_state(heavy_other, 0, 5)) == 0                  # before min_green: stay
    assert a.act(_state(heavy_other, 0, 15)) == 1                 # after min_green, much heavier other axis: switch
    assert a.act(_state([0, 3, 0, 3], 0, 70)) == 0                # max_green reached but nobody waiting: stay green
    assert a.act(_state([1, 3, 1, 3], 0, 70)) == 1                # max_green reached, someone waiting: switch


def test_actuated_gives_green_to_the_heavier_axis_and_extends_when_busy():
    a = _actuated(min_green=10, gap_queue=1, ratio=1.5)
    assert a.act(_state([0, 4, 0, 4], 1, 20)) == 0                # east-west empty, north-south waiting: switch to NS
    assert a.act(_state([5, 0, 5, 0], 0, 20)) == 1                # NS emptied, EW waiting: switch to EW
    assert a.act(_state([4, 5, 4, 5], 0, 20)) == 0                # similar queues: keep the current green
    assert a.act(_state([0, 0, 0, 0], 1, 20)) == 1                # nobody anywhere: stay


def test_actuated_counts_moving_vehicles_like_a_detector_when_attached():
    """The first version counted only halted vehicles, so a busy green axis (vehicles moving, none halted)
    looked empty and was abandoned straight away. With detector-style counts it keeps the green."""
    class Env:
        def approach_vehicle_counts(self):
            return [2, 8, 2, 8]                                   # busy north-south: vehicles are moving

    state = _state([0, 0, 0, 0], 0, 20)                           # nothing halted anywhere
    assert _actuated(min_green=10, ratio=1.5).act(state) == 0     # fallback on halted counts: other axis empty -> stay
    blocked = _state([0, 0, 3, 0], 0, 20)                         # a little halted traffic waiting on east-west
    assert _actuated(min_green=10).act(blocked) == 1              # halted-only view: north-south looks empty -> switch (the bug)
    assert _actuated(min_green=10).attach(Env()).act(blocked) == 0    # detector view: NS has 16 vehicles vs 4 -> keep green
    assert _actuated(min_green=10).attach(Env()).act(_state([0, 0, 3, 0], 0, 70)) == 1   # max green reached: switch


def test_environment_exposes_detector_style_vehicle_counts():
    traci_env.traci = FakeTraci()
    env = traci_env.TraciEnv(CFG)
    assert env.approach_vehicle_counts() == [6, 6, 6, 6]


def test_compare_accepts_a_metric_and_uses_its_own_practical_floor():
    from traffic_drl import cli
    from traffic_drl.compare import MIN_ABS

    args = cli.build_parser().parse_args(["compare", "--scenarios", "tidal", "--controller", "fixed",
                                          "--metric", "avg_wait_per_vehicle"])
    assert args.metric == "avg_wait_per_vehicle" and args.min_abs is None
    assert MIN_ABS["avg_wait_per_vehicle"] == 1.0 and MIN_ABS["mean_total_waiting"] == 2.0


# ------------------------------------------------------------------ Double DQN
def _agent(double):
    ag = DQNAgent(state_dim=1, n_actions=2, hidden_sizes=(4,), batch_size=2, gamma=0.5, double_dqn=double)
    ag.buffer.sample = lambda n: (np.zeros((2, 1)), np.array([0, 1]), np.array([1.0, 1.0]),
                                  np.zeros((2, 1)), np.array([0.0, 0.0]))
    ag.target.forward = lambda x, cache=True: np.tile(np.array([10.0, 1.0]), (len(x), 1))      # target net values
    real_forward = ag.online.forward
    ag.online.forward = lambda x, cache=True: (np.tile(np.array([0.0, 5.0]), (len(x), 1)) if not cache
                                               else real_forward(x, cache))                 # online net prefers action 1
    seen = {}

    def loss_fn(pred, target, mask):
        seen["target"] = target.copy()
        return 0.0, np.zeros_like(pred)
    ag.loss_fn = loss_fn
    ag.online.backward = lambda g: (None, None)
    ag.optimizer.step = lambda *a: None
    return ag, seen


def test_double_dqn_scores_the_online_choice_with_the_target_net():
    plain, seen = _agent(False)
    plain.learn()
    assert seen["target"][0, 0] == 1.0 + 0.5 * 10.0              # max over target values: 10
    double, seen = _agent(True)
    double.learn()
    assert seen["target"][0, 0] == 1.0 + 0.5 * 1.0               # online picks action 1, target values it at 1


def test_double_dqn_flag_comes_from_config():
    cfg = {"dqn": {"hidden_sizes": [4], "double_dqn": True}}
    assert DQNAgent.from_config(cfg, state_dim=3).double_dqn is True
    assert DQNAgent.from_config({"dqn": {"hidden_sizes": [4]}}, state_dim=3).double_dqn is False


# ------------------------------------------------------------------ controller specs
def test_parse_controller_specs():
    assert parse_controller("fixed") == ("fixed", "fixed", "")
    assert parse_controller("fixed:60") == ("fixed:60", "fixed", "60")
    assert parse_controller("act=actuated:min=10,max=60") == ("act", "actuated", "min=10,max=60")
    assert parse_controller("actuated:min=10,max=60")[1:] == ("actuated", "min=10,max=60")
    assert parse_controller(r"best=dqn:C:\models\x.npz") == ("best", "dqn", r"C:\models\x.npz")
    for bad in ("magic", "dqn"):
        try:
            parse_controller(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


# ------------------------------------------------------------------ end to end with a fake simulator
def test_compare_runs_controllers_on_a_scenario_and_writes_reports():
    fake = FakeTraci()
    traci_env.traci = fake
    with tempfile.TemporaryDirectory() as d:
        ckpt = os.path.join(d, "m.npz")
        cfg = load_config(CFG)
        env = traci_env.TraciEnv(CFG)
        DQNAgent.from_config(cfg, state_dim=env.state_size).save(ckpt)
        env.close()
        summary, table = run_comparison(
            CFG, [os.path.join(ROOT, "configs", "scenarios", "tidal.yaml")],
            ["fixed", "actuated:min=10,max=60", f"net=dqn:{ckpt}"], episodes=3, seed_base=30000,
            out_dir=d, env_factory=lambda c, sc: traci_env.TraciEnv(c, scenario=sc), log=lambda *a: None)
        rows = {r["controller"]: r for r in summary}
        assert set(rows) == {"fixed", "actuated:min=10,max=60", "net"}
        assert rows["fixed"]["verdict"] == "reference" and rows["fixed"]["n"] == 3
        assert all(rows[c]["verdict"] in ("tie", "better", "worse", "small") for c in rows if c != "fixed")
        assert "| tidal | fixed |" in table and "Verdict" in table
        for name in ("compare_summary.csv", "compare_summary.md", "compare_episodes.csv"):
            assert os.path.exists(os.path.join(d, name))
        eps = list(csv.DictReader(open(os.path.join(d, "compare_episodes.csv"))))
        assert len(eps) == 3 * 3 and {e["scenario"] for e in eps} == {"tidal"}


def test_compare_command_is_wired_into_the_cli():
    from traffic_drl import cli

    args = cli.build_parser().parse_args(["compare", "--scenarios", "tidal", "--controller", "fixed",
                                          "--controller", "actuated"])
    assert args.episodes == 100 and args.seed_base == 30000 and args.controller == ["fixed", "actuated"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
