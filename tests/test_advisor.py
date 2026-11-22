"""The advisor's decision rule (pure, no SUMO) and one end-to-end run (SUMO)."""
import json
import os

import numpy as np
import pytest

from traffic_drl import advisor, compare, stats


def _data(**means):
    """Synthetic per-episode waiting for each controller: 40 episodes, tight spread around the given mean."""
    rng = np.random.default_rng(0)
    return {c: list(m + rng.normal(0, 0.5, 40)) for c, m in means.items()}


def _comparison(data, reference="fixed"):
    """Summary + episode rows built exactly the way compare.run_comparison builds them."""
    summary, rows = [], []
    ref = data[reference]
    for c, vals in data.items():
        m, half = stats.ci95(vals)
        row = {"scenario": "s", "controller": c, "n": len(vals), "mean": m, "ci95": half}
        if c == reference:
            row.update(change_pct=0.0, p_welch="", verdict="reference")
        else:
            p = stats.welch_t_test(vals, ref)["p"]
            row.update(change_pct=100 * (m - stats.mean(ref)) / stats.mean(ref), p_welch=p,
                       verdict=compare.verdict(stats.mean(ref), m, p, 0.05, 2.0))
        summary.append(row)
        rows += [{"controller": c, "mean_total_waiting": v} for v in vals]
    return summary, rows


def test_rule_recommended_when_it_beats_the_fixed_timer():
    advice = advisor.recommend(*_comparison(_data(fixed=60, rule=40)))
    assert advice["recommended"] == "rule" and advice["change_vs_fixed_pct"] < -30
    assert advice["confidence"] == "firm"
    assert "fewer vehicles waiting" in advisor.headline({**advice, "headline": ""})


def test_fixed_kept_when_nothing_is_clearly_better():
    advice = advisor.recommend(*_comparison(_data(fixed=30, rule=29.5)))   # tiny, not meaningful
    assert advice["recommended"] == "fixed" and "Keep the current" in advisor.headline(advice)


def test_dqn_must_beat_the_rule_not_just_the_fixed_timer():
    advice = advisor.recommend(*_comparison(_data(fixed=60, rule=40, dqn=39.5)))
    assert advice["recommended"] == "rule"
    assert any("does not beat the simpler density rule" in r for r in advice["reasons"])


def test_dqn_recommended_when_it_clearly_beats_the_rule():
    advice = advisor.recommend(*_comparison(_data(fixed=60, rule=40, dqn=30)))
    assert advice["recommended"] == "dqn"


def test_few_episodes_are_flagged_preliminary():
    data = {c: v[:5] for c, v in _data(fixed=60, rule=40).items()}
    advice = advisor.recommend(*_comparison(data))
    assert advice["confidence"] == "preliminary" and any("Only 5 episodes" in r for r in advice["reasons"])


def test_caveats_carry_intake_notes_and_limits():
    advice = advisor.recommend(*_comparison(_data(fixed=60, rule=40)), load_notes=["close to capacity"])
    assert advice["caveats"][0] == "close to capacity" and advisor.LIMITS[0] in advice["caveats"]


def test_requires_the_fixed_baseline():
    summary, rows = _comparison(_data(fixed=60, rule=40))
    with pytest.raises(ValueError, match="fixed timer"):
        advisor.recommend([r for r in summary if r["controller"] != "fixed"], rows)


def test_settings():
    controllers = ["fixed=fixed:40", f"rule={advisor.rule_spec({'max': 50})}", "dqn=dqn:models/x.npz@configs/c.yaml"]
    assert advisor.settings_for("fixed", controllers)["green_seconds_per_direction"] == 40
    rule = advisor.settings_for("rule", controllers)
    assert rule["maximum_green_seconds"] == 50 and rule["minimum_green_seconds"] == 10
    assert advisor.settings_for("dqn", controllers)["model_file"] == "models/x.npz"


def test_end_to_end_on_a_generated_junction(tmp_path):
    pytest.importorskip("traci")
    from traffic_drl import intake

    spec = {"name": "e2e", "demand": {"east": 250, "north": 600, "west": 250, "south": 600}}
    built = intake.build_scenario(spec, tmp_path / "scenario")
    cfg = os.path.join(os.path.dirname(__file__), "..", "configs", "dqn_v_dqfd.yaml")
    advice = advisor.advise(built["scenario_yaml"], str(tmp_path / "out"), config=cfg, episodes=3,
                            load_notes=built["advisories"], log=lambda *_: None)
    assert advice["recommended"] in ("fixed", "rule") and advice["confidence"] == "preliminary"
    saved = json.load(open(tmp_path / "out" / "advice.json"))
    assert saved["headline"] == advice["headline"] and saved["settings"]
