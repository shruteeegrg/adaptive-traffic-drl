"""Interactive demo (Streamlit): fixed-time controller vs the DQN agent.

Run with:  traffic-drl demo      (or: streamlit run traffic_drl/app.py)

Tabs:
  Live demo     pick a scenario, press Run: both controllers drive the same
                traffic (same SUMO seed) side by side, with live queues,
                signal state, counters and a shared "vehicles waiting" chart.
                Needs SUMO.
  Test results  the saved comparison from our fresh-seed test runs
                (no SUMO needed -- the fallback if the live demo cannot run).
  How it works  the idea in plain words.
"""

import os
import tempfile
import time
from pathlib import Path

from traffic_drl import demo_core as core


def queue_bars_html(names, queues, cap: int = 12) -> str:
    """Horizontal bars, one per approach road. Fixed scale (cap = about what one
    approach edge holds) so the bars do not jump around as values change."""
    rows = []
    for name, q in zip(names, queues):
        pct = min(100, 100 * q / cap)
        rows.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px">'
            f'<span style="width:48px;text-transform:capitalize">{name}</span>'
            f'<div style="flex:1;background:#ececea;border-radius:4px;height:12px">'
            f'<div style="width:{pct:.0f}%;background:#2a78d6;height:12px;border-radius:4px"></div></div>'
            f'<span style="width:22px;text-align:right">{q}</span></div>')
    return "".join(rows)


def signal_html(green: int) -> str:
    """Which direction has green. Labelled (GREEN / RED), not colour alone."""
    def box(label, is_green):
        bg, word = ("#1e9e5a", "GREEN") if is_green else ("#c0392b", "RED")
        return (f'<div style="flex:1;background:{bg};color:white;padding:6px 8px;border-radius:6px;'
                f'text-align:center;font-size:13px"><b>{label}</b><br>{word}</div>')
    return (f'<div style="display:flex;gap:8px;margin-bottom:6px">'
            f'{box("North–South", green == 0)}{box("East–West", green == 1)}</div>')


def main() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="Adaptive Traffic Signal Control", layout="wide")
    st.title("Adaptive traffic signals: fixed timer vs a learned (DQN) controller")
    st.caption("A simulated four-way junction in SUMO. The DQN agent looks at the queues and chooses "
               "which direction gets green; the fixed timer just alternates every 40 seconds.")

    live_tab, results_tab, about_tab = st.tabs(["Live demo", "Test results", "How it works"])

    # ---------------------------------------------------------------- live demo
    with st.sidebar:
        st.header("Run a comparison")
        scenario_label = st.selectbox("Traffic scenario", list(core.SCENARIOS))
        checkpoints = core.list_checkpoints()
        checkpoint = st.selectbox("DQN checkpoint", checkpoints or ["(none found in checkpoints/)"])
        seed = st.number_input("Random seed (same traffic for both)", value=40000, step=1)
        delay = st.slider("Playback speed", 0.0, 0.2, 0.05, 0.01,
                          help="Pause per decision. 0 = as fast as possible (a 30-minute episode takes ~2 s).")
        run_clicked = st.button("Run both controllers", type="primary", disabled=not checkpoints)

    with live_tab:
        placeholders = {}
        cols = st.columns(2)
        for col, key in zip(cols, ("fixed", "dqn")):
            with col:
                st.subheader(core.CONTROLLERS[key])
                placeholders[key] = st.empty()
        progress_ph, chart_ph, verdict_ph = st.empty(), st.empty(), st.empty()

        def render(data: dict, names=None):
            names = names or ["east", "north", "west", "south"]
            for key in ("fixed", "dqn"):
                evs = [e for e in data.get(key, []) if e.get("event") in ("step", "done")]
                with placeholders[key].container():
                    if not evs:
                        st.write("waiting for the simulator to start…")
                        continue
                    last = evs[-1]
                    st.markdown(signal_html(last["green"]) + queue_bars_html(names, last["queues"]),
                                unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Vehicles waiting now", last["waiting"])
                    c2.metric("Vehicles served", last["arrived"])
                    c3.metric("Signal switches", last["switches"])
            series = {}
            for key, color in (("fixed", core.GRAY), ("dqn", core.BLUE)):
                evs = [e for e in data.get(key, []) if e.get("event") in ("step", "done")]
                if evs:
                    series[core.SHORT_NAMES[key]] = pd.Series([e["waiting"] for e in evs],
                                                              index=[e["t"] / 60 for e in evs])
            if series:
                df = pd.DataFrame(series)
                colors = {core.SHORT_NAMES["fixed"]: core.GRAY, core.SHORT_NAMES["dqn"]: core.BLUE}
                chart_ph.line_chart(df, color=[colors[c] for c in df.columns],
                                    x_label="simulated minutes", y_label="vehicles waiting", height=260)
            finals = {k: next((e for e in data.get(k, []) if e.get("event") == "done"), None) for k in data}
            if all(finals.get(k) for k in ("fixed", "dqn")):
                verdict_ph.info(core.verdict(finals["fixed"], finals["dqn"]))
            ends = [e for k in ("fixed", "dqn") for e in data.get(k, []) if e.get("event") in ("step", "done")]
            if ends:
                t = max(e["t"] for e in ends)
                total = next((e["episode_length"] for k in data for e in data.get(k, []) if e.get("event") == "start"), 1800)
                progress_ph.progress(min(1.0, t / total), text=f"simulated time: {t / 60:.0f} of {total / 60:.0f} minutes")

        if run_clicked:
            out_dir = tempfile.mkdtemp(prefix="traffic_drl_demo_")
            scenario_yaml = core.SCENARIOS[scenario_label]
            files, procs = {}, {}
            for key in ("fixed", "dqn"):
                files[key] = (os.path.join(out_dir, f"{key}.jsonl"), os.path.join(out_dir, f"{key}.err"))
                cmd = core.build_run_command(key, scenario_yaml, checkpoint, int(seed), float(delay), files[key][0])
                procs[key] = core.launch(cmd, files[key][1])
            data = {"fixed": [], "dqn": []}
            offsets = {"fixed": 0, "dqn": 0}
            started, failed = time.time(), None
            while True:
                for key in data:
                    new, offsets[key] = core.read_new_events(files[key][0], offsets[key])
                    data[key] += new
                render(data, names=next((e["approaches"] for e in data["fixed"] + data["dqn"]
                                         if e.get("event") == "start"), None))
                done = all(any(e.get("event") == "done" for e in data[k]) for k in data)
                dead = [k for k, p in procs.items() if p.poll() not in (None, 0)]
                if done:
                    break
                if dead:
                    failed = dead[0]
                    break
                if time.time() - started > 600:
                    failed = "timeout"
                    break
                time.sleep(0.15)
            for p in procs.values():
                if p.poll() is None:
                    p.terminate()
            if failed:
                msg = core.tail(files[failed][1]) if failed in files else "the run took too long"
                verdict_ph.error("The simulation could not run, so there is nothing to show here. "
                                 "Check that SUMO is installed and SUMO_HOME is set, or use the "
                                 "**Test results** tab, which shows our saved results.\n\n"
                                 f"```\n{msg}\n```")
            st.session_state["last_run"] = {"data": data, "scenario": scenario_label}
        elif "last_run" in st.session_state:
            st.caption(f"Showing the last run: {st.session_state['last_run']['scenario']}")
            data = st.session_state["last_run"]["data"]
            render(data, names=next((e["approaches"] for k in data for e in data[k]
                                     if e.get("event") == "start"), None))
        else:
            st.write("Pick a scenario in the sidebar and press **Run both controllers**.")

    # ------------------------------------------------------------- test results
    with results_tab:
        st.subheader("Our test results")
        st.write("Each number is the average of 10 test episodes of 30 simulated minutes, run on random "
                 "seeds the agent never saw while training. Lower waiting is better; higher vehicles/hour is better.")
        table = core.results_table()
        figure = core.ROOT / "figures" / "compare_final.png"
        if figure.exists():
            st.image(str(figure))
        if table:
            st.dataframe(pd.DataFrame(table), hide_index=True)
        st.markdown(
            "**What this shows.** On *tidal* traffic (heavy one way, then the other) the DQN agent cuts the number "
            "of vehicles waiting by about 91% compared with the fixed timer. On balanced rush-hour traffic and on "
            "very light traffic the fixed timer is still better. The agent was trained only on tidal traffic, so "
            "next we are training it on a mix of scenarios to make it work everywhere.")
        if not table and not figure.exists():
            st.info("No saved results found in the figures/ folder.")

    # ------------------------------------------------------------- how it works
    with about_tab:
        st.subheader("The idea in plain words")
        st.markdown("""
**The problem.** Most traffic lights run on a fixed timer, giving every direction the same green time even
when one road is empty and another is jammed.

**The agent.** A small neural network (a *Deep Q-Network*, written from scratch) controls the lights of a
simulated junction. Every 5 simulated seconds it looks at the situation and picks which direction gets green.

- **What it sees:** the queue and waiting time on each road, which direction currently has green, and how long it has had it.
- **What it decides:** keep the current green, or switch to the other direction (a yellow light is inserted automatically).
- **How it learns:** by trial and error in the simulator, rewarded for keeping fewer vehicles waiting.

**How we test it fairly.** Both controllers get exactly the same traffic (same random seed), and we measure
vehicles waiting, vehicles served per hour and how often the lights switch, on seeds the agent never trained on.

**What we found.** The first version learned to cheat by flipping the light every second; we found it because we
tracked the number of switches, fixed the scoring, and added a test. The trained agent is excellent on uneven
traffic but not yet on balanced or very light traffic, which is what we are working on next.
""")


if __name__ == "__main__":
    main()
