"""The client report: one self-contained HTML page rendered from an advice dict (see traffic_drl.advisor).

No dependencies and no network: the chart is inline SVG and the styles are inline, so the file can be emailed,
archived or printed to PDF from any browser. The page leads with the recommendation, then states what was
assumed about the traffic, shows the evidence, says exactly what to apply and how to check it after rollout,
and ends with the limits and the method, so a reader can judge the claim without trusting the author.
"""

import html
from pathlib import Path

NAMES = {"fixed": "Fixed timer (current)", "rule": "Density rule"}
COLORS = {"fixed": "#8a8985", "rule": "#eb6834", "dqn": "#2a78d6"}   # same colours as the demo and report figures
CSS = """
:root{--ink:#1c1c1a;--muted:#5f5f5b;--line:#dcdcd6;--panel:#f6f6f2;--accent:#1e6b4a}
*{box-sizing:border-box}
body{font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:#fff;margin:0}
main{max-width:860px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:34px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.sub{color:var(--muted);margin:0 0 20px}
.rec{background:var(--panel);border-left:6px solid var(--accent);padding:16px 20px;border-radius:6px}
.rec p{margin:4px 0}.rec .head{font-size:20px;font-weight:650}
.tag{display:inline-block;font-size:13px;padding:1px 8px;border-radius:10px;background:#fff;border:1px solid var(--line);color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:14.5px;margin:8px 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
ul{margin:6px 0 6px 20px;padding:0}li{margin:3px 0}
.note{background:#fff7e6;border:1px solid #f0d9a6;border-radius:6px;padding:8px 12px;margin:8px 0;font-size:15px}
.muted{color:var(--muted);font-size:14px}code{background:var(--panel);padding:1px 5px;border-radius:4px;font-size:14px}
svg text{font:13px system-ui,sans-serif;fill:var(--ink)}
@media print{main{padding:0}h2{break-after:avoid}table,svg,.rec{break-inside:avoid}}
"""


def _e(x) -> str:
    return html.escape(str(x))


def _label(c: str) -> str:
    return NAMES.get(c, f"Learned controller ({c})" if c.startswith("dqn") else c)


def _color(c: str) -> str:
    return COLORS.get(c, COLORS["dqn"] if c.startswith("dqn") else "#666")


def chart_svg(evidence: list, recommended: str) -> str:
    """Horizontal bars of mean vehicles waiting with the 95% confidence interval, lower is better."""
    top = max(e["mean_waiting"] + (e["ci95"] if e["ci95"] == e["ci95"] else 0) for e in evidence) * 1.08 or 1.0
    left, width, row, pad = 190, 520, 38, 8
    h = len(evidence) * row + 34
    x = lambda v: left + width * v / top   # noqa: E731
    out = [f'<svg viewBox="0 0 {left + width + 60} {h}" width="100%" role="img" '
           f'aria-label="Mean vehicles waiting per controller with 95% confidence interval">']
    for i, e in enumerate(evidence):
        y = pad + i * row
        c, m = e["controller"], e["mean_waiting"]
        ci = e["ci95"] if e["ci95"] == e["ci95"] else 0.0
        bold = ' font-weight="700"' if c == recommended else ""
        out.append(f'<text x="{left - 8}" y="{y + 17}" text-anchor="end"{bold}>{_e(_label(c))}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{x(m) - left:.1f}" height="24" rx="3" fill="{_color(c)}"/>')
        out.append(f'<line x1="{x(max(m - ci, 0)):.1f}" x2="{x(m + ci):.1f}" y1="{y + 12}" y2="{y + 12}" stroke="#1c1c1a" stroke-width="2"/>')
        out.append(f'<text x="{x(m + ci) + 8:.1f}" y="{y + 17}">{m:.1f}</text>')
    out.append(f'<text x="{left}" y="{h - 6}" class="axis">vehicles waiting on average (lower is better; line = 95% confidence interval)</text>')
    out.append("</svg>")
    return "".join(out)


def _demand_table(ctx: dict) -> str:
    periods = ctx.get("periods")
    if not periods:
        return ""
    rows, t = [], 0.0
    for p in periods:
        rows.append(f"<tr><td>{t:g}–{t + p['minutes']:g} min</td>"
                    + "".join(f"<td class='n'>{p[a]:g}</td>" for a in ("east", "north", "west", "south")) + "</tr>")
        t += p["minutes"]
    return ("<table><tr><th>Period</th><th class='n'>East</th><th class='n'>North</th><th class='n'>West</th>"
            "<th class='n'>South</th></tr>" + "".join(rows) + "</table><p class='muted'>Vehicles per hour on each approach road.</p>")


def _assumptions(ctx: dict) -> str:
    if not ctx:
        return "<p class='muted'>The traffic assumptions were not recorded with this result.</p>"
    s = ctx.get("summary", {})
    mix = ctx.get("vehicle_mix") or {}
    mix_txt = ", ".join(f"{v:.0%} {k}" for k, v in mix.items()) or "not recorded"
    t = ctx.get("turns", {})
    turn_txt = (f"{t.get('left', 0):.0%} turn left and {t.get('right', 0):.0%} turn right"
                if t.get("left") or t.get("right") else "all vehicles go straight")
    load = (f" Peak load is {s['peak_load']:.2f}, where 1.0 is the most one lane per road can discharge."
            if "peak_load" in s else "")
    return (_demand_table(ctx) + f"<ul><li><b>Vehicle mix:</b> {_e(mix_txt)}.</li><li><b>Turning:</b> {_e(turn_txt)}.</li>"
            f"<li><b>Total:</b> about {s.get('vehicles', 0):.0f} vehicles over {s.get('minutes', 0):.0f} minutes.{_e(load)}</li></ul>")


def _settings(settings: dict) -> str:
    if not settings:
        return ""
    rows = "".join(f"<tr><td>{_e(k.replace('_', ' ').capitalize())}</td><td>{_e(v)}</td></tr>"
                   for k, v in settings.items() if k != "controller")
    return f"<p><b>{_e(settings.get('controller', ''))}</b></p><table>{rows}</table>"


def _evidence_table(evidence: list) -> str:
    rows = []
    for e in evidence:
        ref = e["controller"] == "fixed"
        p = e["p_welch"]
        change = "—" if ref else f"{e['change_vs_fixed_pct']:+.1f}%"
        if ref or p is None or p == "":
            p_txt = "—"
        else:
            p_txt = "<0.001" if p < 0.001 else f"{p:.3f}"
        verdict = "current practice" if ref else e["verdict"]
        rows.append(
            f"<tr><td>{_e(_label(e['controller']))}</td><td class='n'>{e['mean_waiting']:.1f} ± {e['ci95']:.1f}</td>"
            f"<td class='n'>{change}</td><td class='n'>{_e(p_txt)}</td>"
            f"<td class='n'>{e['wait_per_vehicle_s']:.1f}</td><td class='n'>{e['vehicles_per_hour']:.0f}</td>"
            f"<td class='n'>{e['switches']:.0f}</td><td>{_e(verdict)}</td></tr>")
    return ("<table><tr><th>Controller</th><th class='n'>Vehicles waiting</th><th class='n'>Change vs fixed</th>"
            "<th class='n'>p-value</th><th class='n'>Wait per vehicle (s)</th><th class='n'>Vehicles / hour</th>"
            "<th class='n'>Signal switches</th><th>Verdict</th></tr>" + "".join(rows) + "</table>")


def render_report(advice: dict) -> str:
    ctx = advice.get("context", {})
    title = ctx.get("name") or advice.get("scenario", "junction")
    rec = advice["recommended"]
    n = advice["episodes"]
    reasons = "".join(f"<li>{_e(r)}</li>" for r in advice["reasons"])
    caveats = "".join(f"<li>{_e(c)}</li>" for c in advice["caveats"])
    notes = "".join(f"<div class='note'>{_e(c)}</div>" for c in advice["caveats"] if c not in _LIMIT_TEXT())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signal timing recommendation: {_e(title)}</title><style>{CSS}</style></head><body><main>
<h1>Signal timing recommendation</h1>
<p class="sub">Junction: {_e(title)} · {n} simulated runs per controller · generated by traffic-drl</p>
<div class="rec"><p class="head">{_e(advice['headline'])}</p>
<p><span class="tag">Confidence: {_e(advice['confidence'])}</span></p><ul>{reasons}</ul></div>
{notes}
<h2>What we assumed about your traffic</h2>{_assumptions(ctx)}
<h2>What we found</h2>
<p>Every controller was run on exactly the same simulated traffic, {n} times, on random seeds nobody tuned on. "Vehicles waiting"
counts vehicles halted at the junction plus any queueing to enter it, averaged over the run.</p>
{chart_svg(advice['evidence'], rec)}{_evidence_table(advice['evidence'])}
<p class="muted">A controller only counts as better when the difference is statistically significant (p &lt; 0.05) and at least 5% and 2 vehicles waiting.</p>
<h2>What to apply</h2>{_settings(advice.get('settings', {}))}
<h2>How to check it after rollout</h2>
<ul><li>Record vehicle counts per approach before the change and for at least two weeks after, at the same hours of the week.</li>
<li>Compare average queue length or time-in-junction against the simulated figures above. Treat a large gap as a reason to
re-run this analysis with the observed counts, not as a failure of either.</li>
<li>Keep the previous timing plan available so it can be restored immediately if conditions change.</li></ul>
<h2>Limits of this result</h2><ul>{caveats}</ul>
<h2>Method</h2>
<p class="muted">Simulator: SUMO. Controllers evaluated on identical traffic (same random seed per run, starting at {_e(advice.get('seed_base', 'n/a'))}).
Differences tested with Welch's t-test; the table reports mean ± 95% confidence interval. The reference is the fixed timer. A learned
controller is only recommended over the density rule if it beats the rule by the same test. Full per-run data: <code>compare_episodes.csv</code>.</p>
</main></body></html>"""


def _LIMIT_TEXT() -> set:
    from traffic_drl import advisor

    return set(advisor.LIMITS)


def write_report(advice: dict, path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(render_report(advice), encoding="utf-8")
    return str(path)
