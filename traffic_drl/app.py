"""Interactive demo app (Streamlit) — Week 8+.

Run with: streamlit run traffic_drl/app.py
(also reachable via `traffic-drl demo` once cli.py wires it up)

Planned layout:
  - Sidebar: choose controller (Fixed-Timer / DQN Agent), choose scenario
    (rush_hour / low_traffic), Run button.
  - Main area: live-updating plots (reward, average wait time, throughput)
    fed by traffic_drl.viz, reading from the running env/agent loop.
  - Optional: side-by-side mode running both controllers on the same
    scenario for a direct visual comparison.

This file is intentionally a stub in Week 1 — build it out once the env
(Week 2), baseline (Week 8) and viz module (Week 7) exist to plug into it.
"""

def main() -> None:
    try:
        import streamlit as st
    except ImportError:
        print("streamlit not installed yet — this is a Week 8+ stub.")
        return

    st.set_page_config(page_title="Adaptive Traffic Signal Control", layout="wide")
    st.title("Adaptive Traffic Signal Control — DQN vs. Fixed-Timer")
    st.info("Demo app not yet implemented — see traffic_drl/app.py for the planned layout.")


if __name__ == "__main__":
    main()
