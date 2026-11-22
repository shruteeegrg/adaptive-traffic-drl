"""The client report renders from an advice dict, escapes everything, and stays self-contained."""
import os
import re

from traffic_drl import advisor, report

EV = [{"controller": "fixed", "mean_waiting": 67.7, "ci95": 1.6, "n": 30, "change_vs_fixed_pct": 0.0, "p_welch": None,
       "verdict": "reference", "wait_per_vehicle_s": 36.4, "vehicles_per_hour": 1571.0, "switches": 41.0},
      {"controller": "rule", "mean_waiting": 41.2, "ci95": 2.7, "n": 30, "change_vs_fixed_pct": -39.1, "p_welch": 1e-9,
       "verdict": "better", "wait_per_vehicle_s": 28.2, "vehicles_per_hour": 1734.0, "switches": 54.0}]
ADVICE = {"recommended": "rule", "headline": "Use the density-responsive rule: 39% fewer vehicles waiting.",
          "confidence": "moderate", "reasons": ["rule is better"], "evidence": EV, "episodes": 30, "seed_base": 30000,
          "caveats": ["close to <capacity>"] + advisor.LIMITS,
          "settings": {"controller": "density-responsive rule", "minimum_green_seconds": 10.0},
          "context": {"name": "Pulchowk <test>", "periods": [{"minutes": 30, "east": 300, "north": 600, "west": 300, "south": 600}],
                      "vehicle_mix": {"car": 0.75, "bus": 0.25}, "turns": {"left": 0.1, "right": 0.1},
                      "summary": {"vehicles": 900, "minutes": 30, "peak_load": 0.5}}}


def test_report_contains_the_decision_evidence_and_limits():
    page = report.render_report(ADVICE)
    for text in ("Use the density-responsive rule", "Confidence: moderate", "-39.1%", "&lt;0.001", "75% car",
                 "10% turn left", "Minimum green seconds", "Limits of this result", "one lane per road"):
        assert text in page, text
    assert "<svg" in page and "aria-label" in page


def test_report_escapes_user_text_and_is_self_contained():
    page = report.render_report(ADVICE)
    assert "Pulchowk <test>" not in page and "Pulchowk &lt;test&gt;" in page
    assert "close to &lt;capacity&gt;" in page
    assert not re.search(r'(src|href)="https?://', page)                 # nothing fetched from the network
    assert page.count("<h2>") == 6


def test_report_renders_when_nothing_beats_the_fixed_timer_and_context_is_missing():
    advice = {**ADVICE, "recommended": "fixed", "headline": "Keep the current fixed timer.", "context": {},
              "evidence": EV[:1], "settings": {"controller": "fixed timer", "green_seconds_per_direction": 40.0}}
    page = report.render_report(advice)
    assert "Keep the current fixed timer" in page and "not recorded" in page


def test_write_report(tmp_path):
    path = report.write_report(ADVICE, str(tmp_path / "nested" / "report.html"))
    assert os.path.getsize(path) > 2000
