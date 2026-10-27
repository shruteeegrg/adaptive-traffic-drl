"""Interactive demo (Streamlit): fixed-time timer, density rule and DQN agent side by side.

Run with:  traffic-drl demo      (or: streamlit run traffic_drl/app.py)

Tabs:
  Live demo     pick a scenario, press Run: the three controllers drive the same
                traffic (same SUMO seed) side by side, with live queues,
                signal state, counters and a shared "vehicles waiting" chart.
                Needs SUMO.
  Test results  the saved comparison from our 100-episode fresh-seed test runs
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


def junction_html(names, queues, green: int, cap: int = 12) -> str:
    """Top-down schematic of the junction: each road shows its queued vehicles as
    squares lined up at the stop line, with a signal lamp. Drawn from the same
    numbers as the counters (not SUMO's own animation); capped at `cap` squares."""
    size, mid, half, car, step = 300, 150, 22, 8, 10
    lane = 11                                  # vehicle lane offset from the road centre line
    # road name -> (unit vector pointing away from the junction, signal group: 0 = north-south, 1 = east-west)
    away = {"east": ((1, 0), 1), "north": ((0, -1), 0), "west": ((-1, 0), 1), "south": ((0, 1), 0)}
    label_at = {"east": (size - 6, mid + 44, "end"), "north": (mid + 30, 14, "start"),
                "west": (6, mid - 34, "start"), "south": (mid - 30, size - 8, "end")}
    out = [f'<svg viewBox="0 0 {size} {size}" style="width:100%;max-width:340px;display:block;margin:0 auto 6px">',
           f'<rect width="{size}" height="{size}" rx="8" fill="#f4f4f1"/>',
           f'<rect x="0" y="{mid - half}" width="{size}" height="{2 * half}" fill="#6b6b68"/>',
           f'<rect x="{mid - half}" y="0" width="{2 * half}" height="{size}" fill="#6b6b68"/>']
    for (x1, y1, x2, y2) in ((0, mid, mid - half, mid), (mid + half, mid, size, mid),
                             (mid, 0, mid, mid - half), (mid, mid + half, mid, size)):
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#fff" stroke-dasharray="6 5"/>')
    for name, q in zip(names, queues):
        if name not in away:
            continue
        (ux, uy), group = away[name]
        px, py = uy, -ux                       # lane direction: vehicles drive on the right
        for k in range(min(int(q), cap)):
            d = half + 6 + k * step
            cx, cy = mid + ux * d + px * lane, mid + uy * d + py * lane
            out.append(f'<rect x="{cx - car / 2:.0f}" y="{cy - car / 2:.0f}" width="{car}" height="{car}" rx="2" fill="#2a78d6"/>')
        lamp = "#1e9e5a" if green == group else "#c0392b"
        lx, ly = mid + ux * (half + 1) + px * lane, mid + uy * (half + 1) + py * lane
        out.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{lamp}" stroke="#fff" stroke-width="1.5"/>')
        tx, ty, anchor = label_at[name]
        out.append(f'<text x="{tx}" y="{ty}" font-size="11" fill="#333" text-anchor="{anchor}">'
                   f'{name.capitalize()}: {int(q)}</text>')
    out.append("</svg>")
    return "".join(out)


def main() -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="Adaptive Traffic Signal Control", layout="wide")
    st.title("Adaptive traffic signals: fixed timer, density rule and a learned (DQN) controller")
    st.caption("A simulated four-way junction in SUMO. The fixed timer alternates every 40 seconds. The density rule "
               "counts the vehicles on each road and gives green to the busier one, as Nepal's first AI-enabled lights "
               "do. The DQN agent learned its own policy from experience in the simulator.")

    live_tab, results_tab, about_tab = st.tabs(["Live demo", "Test results", "How it works"])

    # ---------------------------------------------------------------- live demo
    with st.sidebar:
        st.header("Run a comparison")
        scenario_label = st.selectbox("Traffic scenario", list(core.SCENARIOS))
        checkpoints = core.list_checkpoints()
        checkpoint_choice = st.selectbox("DQN agent", [core.AUTO] + checkpoints if checkpoints
                                         else ["(none found in models/ or checkpoints/)"])
        seed = st.number_input("Random seed (same traffic for both)", value=40000, step=1)
        delay = st.slider("Playback speed", 0.0, 0.2, 0.05, 0.01,
                          help="Pause per decision. 0 = as fast as possible (a 30-minute episode takes ~2 s).")
        run_clicked = st.button("Run all three controllers", type="primary", disabled=not checkpoints)

    with live_tab:
        placeholders = {}
        cols = st.columns(len(core.KEYS))
        for col, key in zip(cols, core.KEYS):
            with col:
                st.subheader(core.CONTROLLERS[key])
                placeholders[key] = st.empty()
        progress_ph, chart_ph, verdict_ph = st.empty(), st.empty(), st.empty()

        def render(data: dict, names=None):
            names = names or ["east", "north", "west", "south"]
            for key in core.KEYS:
                evs = [e for e in data.get(key, []) if e.get("event") in ("step", "done")]
                with placeholders[key].container():
                    if not evs:
                        st.write("waiting for the simulator to start…")
                        continue
                    last = evs[-1]
                    st.markdown(signal_html(last["green"]) + junction_html(names, last["queues"], last["green"]),
                                unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Vehicles waiting now", last["waiting"])
                    c2.metric("Vehicles served", last["arrived"])
                    c3.metric("Signal switches", last["switches"])
            series = {}
            for key in core.KEYS:
                evs = [e for e in data.get(key, []) if e.get("event") in ("step", "done")]
                if evs:
                    series[core.SHORT_NAMES[key]] = pd.Series([e["waiting"] for e in evs],
                                                              index=[e["t"] / 60 for e in evs])
            if series:
                df = core.align_series(series)
                colors = {core.SHORT_NAMES[k]: core.COLORS[k] for k in core.KEYS}
                chart_ph.line_chart(df, color=[colors[c] for c in df.columns],
                                    x_label="simulated minutes", y_label="vehicles waiting", height=260)
            finals = {k: next((e for e in data.get(k, []) if e.get("event") == "done"), None) for k in data}
            if all(finals.get(k) for k in core.KEYS):
                verdict_ph.info(core.verdict(finals["fixed"], finals["dqn"]) + "\n\n"
                                + core.verdict_vs_rule(finals["rule"], finals["dqn"]))
            ends = [e for k in core.KEYS for e in data.get(k, []) if e.get("event") in ("step", "done")]
            if ends:
                t = max(e["t"] for e in ends)
                total = next((e["episode_length"] for k in data for e in data.get(k, []) if e.get("event") == "start"), 1800)
                progress_ph.progress(min(1.0, t / total), text=f"simulated time: {t / 60:.0f} of {total / 60:.0f} minutes")

        if run_clicked:
            out_dir = tempfile.mkdtemp(prefix="traffic_drl_demo_")
            scenario_yaml = core.SCENARIOS[scenario_label]
            checkpoint = core.resolve_checkpoint(checkpoint_choice, scenario_yaml)
            files, procs = {}, {}
            for key in core.KEYS:
                files[key] = (os.path.join(out_dir, f"{key}.jsonl"), os.path.join(out_dir, f"{key}.err"))
                cmd = core.build_run_command(key, scenario_yaml, checkpoint, int(seed), float(delay), files[key][0])
                procs[key] = core.launch(cmd, files[key][1])
            data = {k: [] for k in core.KEYS}
            offsets = {k: 0 for k in core.KEYS}
            started, failed = time.time(), None
            while True:
                for key in data:
                    new, offsets[key] = core.read_new_events(files[key][0], offsets[key])
                    data[key] += new
                render(data, names=next((e["approaches"] for e in sum(data.values(), [])
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
            st.write("Pick a scenario in the sidebar and press **Run all three controllers**.")

    # ------------------------------------------------------------- test results
    with results_tab:
        st.subheader("Our test results")
        st.write("Every number is the mean of 100 test episodes of 30 simulated minutes, on random seeds nobody trained or tuned on, "
                 "with identical traffic for every controller. Lower waiting is better. Each learned agent is a separately trained "
                 "model, and all four per scenario are reported, not just the best.")
        for name, caption in (("final_results.png", "Each dot is one trained agent, compared with the tuned density rule."),
                              ("regime_map.png", "Where the density rule helps against a fixed timer, by demand level and how uneven it is.")):
            figure = core.ROOT / "figures" / "report" / name
            if figure.exists():
                st.image(str(figure), caption=caption)
        table = core.final_results_markdown()
        if table:
            st.markdown(table)
        st.markdown(
            "**What this shows.**\n\n"
            "- A density rule (count the vehicles, give green to the busier road) beats the fixed timer in every one of 16 demand patterns we tried, "
            "by 20 to 98%.\n"
            "- A DQN trained from the rule's demonstrations **matches** that rule. In some heavy, uneven cases an agent is about 10% better, "
            "but that depends on which training run you get: some agents tie or lose.\n"
            "- One model for every demand pattern does not yet match the rule on traffic it has not seen (light traffic is the weakest case).\n"
            "- Under very heavy load the junction is full and no controller can help much.")
        if not table:
            st.info("No saved results found (docs/results_final.md).")

    # ------------------------------------------------------------- how it works
    with about_tab:
        st.subheader("The idea in plain words")
        st.markdown("""
**The problem.** Most traffic lights run on a fixed timer, giving every direction the same green time even
when one road is empty and another is jammed.

**The agent.** A small neural network (a *Deep Q-Network*, written from scratch) controls the lights of a
simulated junction. Every 5 simulated seconds it looks at the situation and picks which direction gets green.

- **What it sees:** the queue, the number of vehicles and the waiting time on each road, which direction currently has green, and how long it has had it.
- **What it decides:** keep the current green, or switch to the other direction (a yellow light is inserted automatically).
- **How it learns:** by trial and error in the simulator, rewarded for keeping fewer vehicles waiting.

**How we test it fairly.** All three controllers get exactly the same traffic (same random seed). We measure
vehicles waiting, vehicles served per hour and how often the lights switch, on seeds the agent never trained on,
with 100 episodes per comparison, confidence intervals and significance tests.

**What we found.** The first versions of the agent were unstable and often lost to a well-set density rule. Giving
the agent the rule's demonstrations (and keeping them in memory, with a loss that stops it drifting away from them)
made training reliable. It now matches the rule, and sometimes beats it by about 10% where the traffic is heavy and
uneven. We report all trained agents, including the ones that did not.
""")


if __name__ == "__main__":
    main()
