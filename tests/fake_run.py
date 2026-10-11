"""Stand-in for `traffic-drl run`: writes the same JSON-lines stream without
SUMO, so the demo app's polling and drawing can be tested end to end."""
import argparse
import json
import time

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--controller", required=True)
ap.add_argument("--fail", action="store_true")
a = ap.parse_args()
if a.fail:
    raise SystemExit("sumo: command not found (pretend)")
scale = 1.0 if a.controller == "fixed" else 0.4          # pretend the DQN waits less
with open(a.out, "w") as f:
    def emit(e):
        f.write(json.dumps(e) + "\n"); f.flush()
    emit({"event": "start", "controller": a.controller, "scenario": "fake", "approaches": ["east", "north", "west", "south"], "episode_length": 300})
    for i in range(1, 31):
        snap = {"t": i * 10.0, "queues": [i % 5, 2, i % 3, 1], "backlog": i, "waiting": int((i + 5) * scale * 4),
                "green": (i // 5) % 2, "mean_queue": 3.0, "mean_backlog": 2.0,
                "mean_total_waiting": 100.0 * scale, "avg_wait_per_vehicle": 10.0,
                "throughput_per_hour": 2000.0 + (500 if a.controller == "dqn" else 0), "arrived": i * 3,
                "switches": i // 5, "ns_green_fraction": 0.5}
        emit({"event": "done" if i == 30 else "step", **snap})
        time.sleep(0.01)
