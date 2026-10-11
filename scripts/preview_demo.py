"""Preview the demo app WITHOUT SUMO: the Live demo tab is fed by a fake
simulator (tests/fake_run.py), so the layout and animation can be seen on a
machine that has no SUMO. The numbers on that tab are made up; the Test results
and How it works tabs show the real saved results.

    streamlit run scripts/preview_demo.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from traffic_drl import app, demo_core as core  # noqa: E402


def fake_command(controller, scenario_yaml, checkpoint, seed, delay, out_path):
    return [sys.executable, str(ROOT / "tests" / "fake_run.py"), "--controller", controller, "--out", out_path]


core.build_run_command = fake_command
app.main()
