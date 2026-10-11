"""Run one controller on one scenario and stream what happens as JSON lines.

This is what the demo app launches (one process per controller) so the two
controllers can run side by side. Each line is one event:
  {"event": "start", "controller", "scenario", "approaches", "episode_length"}
  {"event": "step",  "t", "queues", "backlog", "waiting", "green", <metrics>}   (one per decision)
  {"event": "done",  ... same fields as a step ...}                              (last line)
`delay` slows playback so a 30-minute simulated episode (about 2 s of real
time) can be watched.
"""

import json
import time


def stream_run(env, agent, out_path: str, controller: str, scenario_name: str, delay: float = 0.0) -> dict:
    """Play one greedy episode, appending events to `out_path`. Returns the final snapshot."""
    with open(out_path, "w") as f:
        def emit(event: dict) -> None:
            f.write(json.dumps(event) + "\n")
            f.flush()   # the app reads the file while it is still being written

        names = [a["name"] for a in env.approaches]
        state = env.reset()
        if hasattr(agent, "reset"):
            agent.reset()
        emit({"event": "start", "controller": controller, "scenario": scenario_name,
              "approaches": names, "episode_length": env.episode_length})
        while True:
            action = agent.act(state, greedy=True)
            state, _, done, _ = env.step(action)
            snap = env.snapshot()
            emit({"event": "done" if done else "step", **snap})
            if done:
                return snap
            if delay:
                time.sleep(delay)
