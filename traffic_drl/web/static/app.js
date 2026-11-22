"use strict";
/* Signal Studio front end: plain JavaScript, no build step. Talks only to /api/* (see traffic_drl/web/server.py). */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const APPROACHES = ["north", "east", "south", "west"];
const TYPES = [
  { key: "motorcycle", label: "Motorcycles", color: "#e8891d", len: 13, wid: 6 },
  { key: "car", label: "Cars", color: "#2a78d6", len: 22, wid: 11 },
  { key: "bus", label: "Buses", color: "#7a4fd1", len: 38, wid: 14 },
  { key: "goods", label: "Light goods", color: "#2f9e9e", len: 27, wid: 12 },
];
const CONTROLLERS = [
  { key: "fixed", name: "Fixed timer", color: "#8a8985", sub: "Alternates every 40 seconds, whatever the traffic does." },
  { key: "rule", name: "Density rule", color: "#eb6834", sub: "Counts vehicles on each road and gives green to the busier one." },
  { key: "dqn", name: "Trained agent", color: "#2a78d6", sub: "A neural network that learned its policy in the simulator." },
];
const PRESETS = [
  { name: "Balanced", rates: { north: 500, east: 500, south: 500, west: 500 }, swap: false },
  { name: "Morning rush, north–south heavy", rates: { north: 800, east: 350, south: 800, west: 350 }, swap: false },
  { name: "Tidal swing", rates: { north: 900, east: 300, south: 900, west: 300 }, swap: true },
  { name: "Near capacity", rates: { north: 850, east: 850, south: 850, west: 850 }, swap: false },
  { name: "Quiet period", rates: { north: 120, east: 120, south: 120, west: 120 }, swap: false },
];
const DEFAULTS = {
  rates: { north: 600, east: 400, south: 600, west: 400 },
  mix: { motorcycle: 62, car: 22, bus: 8, goods: 8 },
  turns: { left: 10, right: 10 }, minutes: 30, swap: false,
};
const TRAIN_SECONDS_PER_EPISODE = 2.5, TRAIN_SECONDS_PER_SEED = 65;

const state = {
  t: structuredClone(DEFAULTS), valid: true, dirty: true, scenarioId: null,
  agents: [], agentId: "generalist", speed: "normal", seedCounter: 0,
  compare: null, evalRuns: 30, evalId: null, trainId: null, unlocked: 1, preset: null,
};

/* ───────────── helpers ───────────── */
function toast(msg, ms = 4200) {
  const el = $("#toast"); el.textContent = msg; el.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => (el.hidden = true), ms);
}
async function api(path, opts = {}) {
  const init = { method: opts.method || (opts.body ? "POST" : "GET"), headers: {} };
  if (opts.body) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.body); }
  const res = await fetch(path, init);
  let data = null; try { data = await res.json(); } catch (_) { /* not JSON */ }
  if (!res.ok) { const e = new Error((data && (data.error || data.detail)) || res.statusText); e.status = res.status; throw e; }
  return data;
}
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const store = {
  get() { try { return JSON.parse(localStorage.getItem("signal-studio") || "null"); } catch (_) { return null; } },
  set(v) { try { localStorage.setItem("signal-studio", JSON.stringify(v)); } catch (_) { /* private mode */ } },
};
const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); e.innerHTML = html; return e; };
const num = (v, d = 1) => Number(v).toFixed(d);

/* ───────────── navigation ───────────── */
function goStep(n) {
  $$(".step").forEach((s) => s.classList.toggle("show", s.id === "step" + n));
  $$("#steps button").forEach((b) => {
    const k = +b.dataset.step;
    b.classList.toggle("on", k === n); b.disabled = k > state.unlocked;
    b.classList.toggle("done", k < n && k <= state.unlocked);
  });
  window.scrollTo({ top: 0 });
  if (n === 1) startJunction(); else stopJunction();
}
function unlock(n) { state.unlocked = Math.max(state.unlocked, n); $$("#steps button").forEach((b) => { b.disabled = +b.dataset.step > state.unlocked; }); }
$("#steps").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b && !b.disabled) goStep(+b.dataset.step); });

/* ───────────── step 1: traffic ───────────── */
function payload() {
  return { rates: state.t.rates, minutes: state.t.minutes, swap: state.t.swap, mix_pct: state.t.mix, turns_pct: state.t.turns };
}
function renderMix() {
  const total = Object.values(state.t.mix).reduce((a, b) => a + b, 0) || 1;
  $("#mixbar").innerHTML = TYPES.map((t) => `<i style="width:${(100 * state.t.mix[t.key] / total).toFixed(1)}%;background:${t.color}"></i>`).join("");
  const root = $("#mixes");
  if (!root.children.length) {
    root.innerHTML = TYPES.map((t) => `<div class="row mix"><label for="m-${t.key}"><span class="sw" style="background:${t.color}"></span>${t.label}</label><input id="m-${t.key}" type="range" min="0" max="100"><output id="o-m-${t.key}"></output></div>`).join("");
    TYPES.forEach((t) => $("#m-" + t.key).addEventListener("input", (e) => { state.t.mix[t.key] = +e.target.value; changed(); }));
  }
  TYPES.forEach((t) => {
    $("#m-" + t.key).value = state.t.mix[t.key];
    $("#o-m-" + t.key).textContent = Math.round(100 * state.t.mix[t.key] / total) + "%";
  });
}
function syncInputs() {
  APPROACHES.forEach((a) => { $("#r-" + a).value = state.t.rates[a]; });
  $("#t-left").value = state.t.turns.left; $("#t-right").value = state.t.turns.right;
  $("#o-t-left").textContent = state.t.turns.left + "%"; $("#o-t-right").textContent = state.t.turns.right + "%";
  $("#minutes").value = state.t.minutes; $("#o-minutes").textContent = state.t.minutes + " min";
  $("#swap").checked = state.t.swap;
  renderMix();
}
const preview = debounce(async () => {
  try {
    const r = await api("/api/preview", { body: payload() });
    state.valid = true; $("#traffic-error").hidden = true;
    const load = r.summary.peak_load;
    $("#loadv").textContent = load.toFixed(2);
    $("#loadw").textContent = load < 0.15 ? "very light" : load <= 0.9 ? "comfortable" : load <= 1 ? "close to capacity" : "over capacity";
    $("#marker").style.left = Math.min(load / 1.2, 1) * 100 + "%";
    $("#advisories").innerHTML = ""; r.advisories.forEach((t) => { const d = el("div", { className: "adv" }); d.textContent = t; $("#advisories").append(d); });
  } catch (e) {
    state.valid = false; $("#traffic-error").hidden = false; $("#traffic-error").textContent = e.message;
  }
  $("#goCompare").disabled = !state.valid;
}, 180);
function changed() {
  state.dirty = true; state.preset = null; $$("#presets button").forEach((b) => b.classList.remove("on"));
  renderMix(); preview(); store.set({ t: state.t });
}
function bindTraffic() {
  const saved = store.get(); if (saved && saved.t) state.t = { ...structuredClone(DEFAULTS), ...saved.t };
  $("#presets").innerHTML = PRESETS.map((p, i) => `<button data-i="${i}">${p.name}</button>`).join("");
  $("#presets").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return; const p = PRESETS[+b.dataset.i];
    Object.assign(state.t, { rates: { ...p.rates }, swap: p.swap, mix: { ...DEFAULTS.mix }, turns: { ...DEFAULTS.turns }, minutes: 30 });
    syncInputs(); state.dirty = true; preview(); store.set({ t: state.t });
    $$("#presets button").forEach((x) => x.classList.toggle("on", x === b));
  });
  APPROACHES.forEach((a) => {
    const input = $("#r-" + a);
    input.addEventListener("input", () => { state.t.rates[a] = Math.max(0, Math.min(1500, +input.value || 0)); changed(); });
    $$(".arm." + a + " .num button").forEach((b) => b.addEventListener("click", () => {
      state.t.rates[a] = Math.max(0, Math.min(1500, state.t.rates[a] + +b.dataset.d)); input.value = state.t.rates[a]; changed();
    }));
  });
  ["left", "right"].forEach((k) => $("#t-" + k).addEventListener("input", (e) => { state.t.turns[k] = +e.target.value; $("#o-t-" + k).textContent = e.target.value + "%"; changed(); }));
  $("#minutes").addEventListener("input", (e) => { state.t.minutes = +e.target.value; $("#o-minutes").textContent = e.target.value + " min"; changed(); });
  $("#swap").addEventListener("change", (e) => { state.t.swap = e.target.checked; changed(); });
  syncInputs(); preview();
  $("#goCompare").addEventListener("click", () => { goStep(2); startCompare(); });
}

/* the illustration: vehicles drift toward the junction at a rate that follows the volume and in the chosen mix */
const J = { raf: 0, last: 0, cars: [], ctx: null };
const DIRS = { north: [0, -1], south: [0, 1], east: [1, 0], west: [-1, 0] };
function startJunction() {
  const c = $("#jc"); if (!c || J.raf) return;
  J.ctx = c.getContext("2d"); J.last = performance.now();
  const loop = (now) => { J.raf = requestAnimationFrame(loop); drawJunction(Math.min(0.05, (now - J.last) / 1000)); J.last = now; };
  J.raf = requestAnimationFrame(loop);
}
function stopJunction() { cancelAnimationFrame(J.raf); J.raf = 0; }
function pickType() {
  const mix = state.t.mix, total = Object.values(mix).reduce((a, b) => a + b, 0) || 1; let r = Math.random() * total;
  for (const t of TYPES) { r -= mix[t.key]; if (r <= 0) return t; } return TYPES[1];
}
function drawJunction(dt) {
  const c = $("#jc"), dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight; if (!w) return;
  if (c.width !== Math.round(w * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
  const g = J.ctx; g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  const cx = w / 2, cy = h / 2, rw = Math.min(w, h) * 0.17, lane = rw * 0.26;
  g.fillStyle = "#6b7378"; g.fillRect(0, cy - rw, w, rw * 2); g.fillRect(cx - rw, 0, rw * 2, h);
  g.strokeStyle = "rgba(255,255,255,.85)"; g.lineWidth = 2; g.setLineDash([10, 9]);
  [[0, cy, cx - rw, cy], [cx + rw, cy, w, cy], [cx, 0, cx, cy - rw], [cx, cy + rw, cx, h]].forEach(([a, b, x, y]) => { g.beginPath(); g.moveTo(a, b); g.lineTo(x, y); g.stroke(); });
  g.setLineDash([]);
  const speed = Math.min(w, h) * 0.34;
  APPROACHES.forEach((a) => {
    const [ux, uy] = DIRS[a], armLen = (a === "north" || a === "south" ? h : w) / 2;
    const rate = state.t.rates[a] / 3600 * 7;                       // 7x faster than real time, so the illustration is lively
    const farthest = Math.max(-1e9, ...J.cars.filter((v) => v.a === a).map((v) => v.d));   // nearest the road's far end
    if (Math.random() < rate * dt && farthest < armLen - 52) {      // keep a gap behind the previous vehicle
      J.cars.push({ a, d: armLen + 20, t: pickType(), s: speed * 0.9 });
    }
  });
  const next = [];
  J.cars.forEach((v) => {
    const [ux, uy] = DIRS[v.a], armLen = (v.a === "north" || v.a === "south" ? h : w) / 2;
    v.d -= v.s * dt; if (v.d < -armLen - 30) return; next.push(v);
    const px = uy, py = -ux, x = cx + ux * v.d + px * lane, y = cy + uy * v.d + py * lane;
    g.save(); g.translate(x, y); g.rotate(Math.atan2(-uy, -ux)); g.fillStyle = v.t.color;
    g.beginPath(); g.roundRect(-v.t.len / 2, -v.t.wid / 2, v.t.len, v.t.wid, 2); g.fill(); g.restore();
  });
  J.cars = next;
}

/* ───────────── step 2: live comparison ───────────── */
function buildTrio() {
  $("#trio").innerHTML = CONTROLLERS.map((c) => `
    <div class="card ctl" id="ctl-${c.key}">
      <h2><i style="background:${c.color}"></i>${c.name}</h2><p class="sub">${c.sub}</p>
      <div class="lamps"><div class="lamp" data-g="0">North–South</div><div class="lamp" data-g="1">East–West</div></div>
      <div class="jsvg"></div>
      <div class="metrics"><div><b data-m="waiting">–</b><span>waiting now</span></div><div><b data-m="arrived">–</b><span>served</span></div><div><b data-m="switches">–</b><span>switches</span></div></div>
    </div>`).join("");
  $("#legend").innerHTML = CONTROLLERS.map((c) => `<span><i class="sw" style="background:${c.color}"></i>${c.name}</span>`).join("");
}
function junctionSVG(names, queues, green, color, cap = 12) {
  const size = 300, mid = 150, half = 22, car = 8, step = 10, lane = 11;
  const away = { east: [[1, 0], 1], north: [[0, -1], 0], west: [[-1, 0], 1], south: [[0, 1], 0] };
  const labelAt = { east: [size - 6, mid + 44, "end"], north: [mid + 30, 14, "start"], west: [6, mid - 34, "start"], south: [mid - 30, size - 8, "end"] };
  let o = `<svg viewBox="0 0 ${size} ${size}" role="img" aria-label="Queues at the junction"><rect width="${size}" height="${size}" rx="8" fill="#eef1ee"/>`;
  o += `<rect x="0" y="${mid - half}" width="${size}" height="${2 * half}" fill="#6b7378"/><rect x="${mid - half}" y="0" width="${2 * half}" height="${size}" fill="#6b7378"/>`;
  [[0, mid, mid - half, mid], [mid + half, mid, size, mid], [mid, 0, mid, mid - half], [mid, mid + half, mid, size]]
    .forEach(([a, b, c, d]) => { o += `<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" stroke="#fff" stroke-dasharray="6 5"/>`; });
  names.forEach((n, i) => {
    if (!away[n]) return; const [[ux, uy], grp] = away[n], px = uy, py = -ux, q = queues[i] || 0;
    for (let k = 0; k < Math.min(q, cap); k++) { const d = half + 6 + k * step; o += `<rect x="${(mid + ux * d + px * lane - car / 2).toFixed(0)}" y="${(mid + uy * d + py * lane - car / 2).toFixed(0)}" width="${car}" height="${car}" rx="2" fill="${color}" stroke="#fff" stroke-width="1"/>`; }
    o += `<circle cx="${mid + ux * (half + 1) + px * lane}" cy="${mid + uy * (half + 1) + py * lane}" r="5" fill="${green === grp ? "#1e9e5a" : "#c0392b"}" stroke="#fff" stroke-width="1.5"/>`;
    const [tx, ty, an] = labelAt[n]; o += `<text x="${tx}" y="${ty}" font-size="11" fill="#12202e" text-anchor="${an}">${n[0].toUpperCase() + n.slice(1)}: ${q}</text>`;
  });
  return o + "</svg>";
}
function drawLamps(card, green) {
  $$(".lamp", card).forEach((l) => { const on = +l.dataset.g === green; l.style.background = on ? "#1e9e5a" : "#c0392b"; l.textContent = (+l.dataset.g ? "East–West " : "North–South ") + (on ? "GREEN" : "RED"); });
}
function drawWaitChart(series, total) {
  const W = 900, H = 262, L = 46, R = 14, T = 12, B = 46;
  const maxY = Math.max(10, ...CONTROLLERS.flatMap((c) => series[c.key].map((p) => p.w))) * 1.1, maxX = (total || 1800) / 60;
  const x = (m) => L + (W - L - R) * m / maxX, y = (v) => H - B - (H - T - B) * v / maxY;
  let o = "";
  for (let i = 0; i <= 4; i++) { const v = maxY * i / 4; o += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#e5e9e7"/><text x="${L - 8}" y="${y(v) + 4}" font-size="12" text-anchor="end" fill="#5d6b78">${Math.round(v)}</text>`; }
  for (let m = 0; m <= maxX; m += maxX > 20 ? 5 : 2.5) o += `<text x="${x(m)}" y="${H - 28}" font-size="12" text-anchor="middle" fill="#5d6b78">${m}</text>`;
  o += `<text x="${(L + W - R) / 2}" y="${H - 6}" font-size="12" text-anchor="middle" fill="#5d6b78">simulated minutes</text>`;
  CONTROLLERS.forEach((c) => { const pts = series[c.key]; if (pts.length) o += `<polyline fill="none" stroke="${c.color}" stroke-width="2.4" stroke-linejoin="round" points="${pts.map((p) => x(p.t / 60).toFixed(1) + "," + y(p.w).toFixed(1)).join(" ")}"/>`; });
  $("#wait").innerHTML = o;
}
function verdictText(fin) {
  const f = fin.fixed.mean_total_waiting, r = fin.rule.mean_total_waiting, d = fin.dqn.mean_total_waiting, pct = (a, b) => Math.round(Math.abs(a - b) / Math.max(b, 1e-9) * 100);
  const lines = [];
  if (f < 0.5 && r < 0.5) lines.push("Traffic was so light that every controller kept vehicles moving; there is nothing to separate them.");
  else lines.push(r < f * 0.95 ? `The density rule had <b>${pct(r, f)}% fewer vehicles waiting</b> than the fixed timer (${num(r)} vs ${num(f)}).`
    : r > f * 1.05 ? `Here the fixed timer did better than the density rule (${num(f)} vs ${num(r)} vehicles waiting).` : `The density rule and the fixed timer were about level (${num(r)} vs ${num(f)}).`);
  lines.push(Math.abs(d - r) < Math.max(0.05 * r, 2) ? `The trained agent and the density rule are about level here (${num(d)} vs ${num(r)}).`
    : d < r ? `The trained agent had <b>${pct(d, r)}% fewer vehicles waiting</b> than the density rule (${num(d)} vs ${num(r)}).` : `Here the density rule did better: the trained agent had ${pct(d, r)}% more vehicles waiting (${num(d)} vs ${num(r)}).`);
  return `<p>${lines.join("</p><p>")}</p><small>One run is a single sample. The next step repeats it on fresh random traffic and tests the differences.</small>`;
}
async function ensureScenario() {
  if (state.scenarioId && !state.dirty) return state.scenarioId;
  const s = await api("/api/scenario", { body: payload() }); state.scenarioId = s.id; state.dirty = false; return s.id;
}
async function startCompare() {
  clearInterval(state.poll); $("#goEval").disabled = true; $("#verdict").hidden = true; $("#runstatus").textContent = "Starting the simulator…";
  const series = { fixed: [], rule: [], dqn: [] }, last = {}, counts = { fixed: 0, rule: 0, dqn: 0 }; let names = ["east", "north", "west", "south"], total = 1800;
  buildTrio(); drawWaitChart(series, total);
  let run;
  try { await ensureScenario(); run = await api("/api/compare", { body: { scenario_id: state.scenarioId, agent_id: state.agentId, seed: 40000 + state.seedCounter++ * 7, speed: state.speed } }); }
  catch (e) { $("#runstatus").textContent = ""; toast("Could not start the comparison: " + e.message); return; }
  unlock(4); unlock(2); goStepButtons();
  const tick = async () => {
    let r; try { r = await api(`/api/compare/${run.id}?fixed=${counts.fixed}&rule=${counts.rule}&dqn=${counts.dqn}`); } catch (e) { clearInterval(state.poll); toast(e.message); return; }
    CONTROLLERS.forEach((c) => {
      counts[c.key] = r.counts[c.key];
      r.events[c.key].forEach((ev) => {
        if (ev.event === "start") { names = ev.approaches; total = ev.episode_length; return; }
        series[c.key].push({ t: ev.t, w: ev.waiting }); last[c.key] = ev;
      });
      const ev = last[c.key], card = $("#ctl-" + c.key);
      if (ev) {
        $(".jsvg", card).innerHTML = junctionSVG(names, ev.queues, ev.green, c.color); drawLamps(card, ev.green);
        $('[data-m="waiting"]', card).textContent = ev.waiting; $('[data-m="arrived"]', card).textContent = ev.arrived; $('[data-m="switches"]', card).textContent = ev.switches;
      }
    });
    drawWaitChart(series, total);
    const t = Math.max(0, ...Object.values(last).map((e) => e.t || 0));
    $("#runstatus").textContent = r.done ? "Finished" : `Simulated time ${Math.round(t / 60)} of ${Math.round(total / 60)} min`;
    if (r.failed) { clearInterval(state.poll); $("#runstatus").textContent = ""; toast("The simulation could not run: " + r.failed.split("\n").pop(), 9000); }
    if (r.done) {
      clearInterval(state.poll); $("#verdict").innerHTML = verdictText(last); $("#verdict").hidden = false;
      $("#goEval").disabled = false; unlock(3); goStepButtons();
    }
  };
  state.poll = setInterval(tick, 220); tick();
}
function goStepButtons() { $$("#steps button").forEach((b) => { b.disabled = +b.dataset.step > state.unlocked; }); }
async function loadAgents(selectId) {
  const r = await api("/api/agents"); state.agents = r.agents;
  if (selectId) state.agentId = selectId;
  if (!state.agents.some((a) => a.id === state.agentId)) state.agentId = state.agents.length ? state.agents[0].id : "generalist";
  const sel = $("#agent"); sel.innerHTML = state.agents.map((a) => `<option value="${a.id}">${a.label}</option>`).join(""); sel.value = state.agentId;
  const a = state.agents.find((x) => x.id === state.agentId); $("#agentnote").textContent = a ? a.note : "";
}
function bindCompare() {
  $("#agent").addEventListener("change", (e) => { state.agentId = e.target.value; const a = state.agents.find((x) => x.id === state.agentId); $("#agentnote").textContent = a ? a.note : ""; });
  $("#speed").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; state.speed = b.dataset.v; $$("#speed button").forEach((x) => x.classList.toggle("on", x === b)); });
  $("#rerun").addEventListener("click", startCompare);
  $("#goEval").addEventListener("click", () => goStep(3));
}

/* ───────────── step 3: evaluation ───────────── */
function barChart(evidence, recommended) {
  const label = (c) => (c === "fixed" ? "Fixed timer (current)" : c === "rule" ? "Density rule" : "Trained agent");
  const color = (c) => (c === "fixed" ? "#8a8985" : c === "rule" ? "#eb6834" : "#2a78d6");
  const top = Math.max(...evidence.map((e) => e.mean_waiting + (e.ci95 || 0))) * 1.1 || 1, left = 170, width = 520, row = 40, H = evidence.length * row + 30;
  const x = (v) => left + width * v / top;
  let o = `<svg viewBox="0 0 ${left + width + 60} ${H}" width="100%" role="img" aria-label="Mean vehicles waiting with 95% confidence interval">`;
  evidence.forEach((e, i) => {
    const y = 6 + i * row, ci = e.ci95 || 0, bold = e.controller === recommended ? ' font-weight="700"' : "";
    o += `<text x="${left - 10}" y="${y + 18}" text-anchor="end" font-size="14"${bold} fill="#12202e">${label(e.controller)}</text>`;
    o += `<rect x="${left}" y="${y}" width="${x(e.mean_waiting) - left}" height="26" rx="4" fill="${color(e.controller)}"/>`;
    o += `<line x1="${x(Math.max(e.mean_waiting - ci, 0))}" x2="${x(e.mean_waiting + ci)}" y1="${y + 13}" y2="${y + 13}" stroke="#12202e" stroke-width="2"/>`;
    o += `<text x="${x(e.mean_waiting + ci) + 8}" y="${y + 18}" font-size="14" fill="#12202e">${num(e.mean_waiting)}</text>`;
  });
  return o + `<text x="${left}" y="${H - 6}" font-size="12" fill="#5d6b78">average vehicles waiting (lower is better; line is the 95% confidence interval)</text></svg>`;
}
function pTxt(p) { return p === null || p === "" || p === undefined ? "—" : p < 0.001 ? "<0.001" : p.toFixed(3); }
function renderResult(r) {
  const a = r.advice, ctrl = (c) => (c === "fixed" ? "Fixed timer (current)" : c === "rule" ? "Density rule" : "Trained agent");
  const rows = a.evidence.map((e) => `<tr><td>${ctrl(e.controller)}</td><td class="n">${num(e.mean_waiting)} ± ${num(e.ci95)}</td><td class="n">${e.controller === "fixed" ? "—" : (e.change_vs_fixed_pct > 0 ? "+" : "") + num(e.change_vs_fixed_pct) + "%"}</td><td class="n">${e.controller === "fixed" ? "—" : pTxt(e.p_welch)}</td><td class="n">${num(e.wait_per_vehicle_s)}</td><td class="n">${Math.round(e.vehicles_per_hour)}</td><td>${e.controller === "fixed" ? "current practice" : e.verdict}</td></tr>`).join("");
  const settings = Object.entries(a.settings).filter(([k]) => k !== "controller").map(([k, v]) => `<tr><td>${k.replace(/_/g, " ").replace(/^./, (s) => s.toUpperCase())}</td><td>${v}</td></tr>`).join("");
  const root = $("#evalresult");
  root.innerHTML = `<div class="result">
    <div class="card headline"><div class="big"></div><span class="tag"></span><ul></ul></div>
    <div class="card"><h3>What we found</h3>${barChart(a.evidence, a.recommended)}
      <div style="overflow-x:auto"><table><tr><th>Controller</th><th class="n">Vehicles waiting</th><th class="n">Change vs fixed</th><th class="n">p-value</th><th class="n">Wait / vehicle (s)</th><th class="n">Vehicles / hour</th><th>Verdict</th></tr>${rows}</table></div>
      <p class="hint" style="margin-top:8px">Better means statistically significant (p &lt; 0.05) and at least 5% and 2 vehicles waiting.</p></div>
    <div class="cols"><div class="card"><h3>What to apply</h3><p><b></b></p><table class="kv">${settings}</table></div>
      <div class="card"><h3>Limits of this result</h3><ul class="list" id="caveats"></ul></div></div>
    <div class="linkrow"><a class="cta" href="${r.report_url}" target="_blank" rel="noopener">Open the full report</a><button class="ghost" id="toTrain">Train an agent on this traffic →</button></div></div>`;
  $(".headline .big", root).textContent = a.headline; $(".headline .tag", root).textContent = "Confidence: " + a.confidence;
  a.reasons.forEach((t) => { const li = el("li"); li.textContent = t; $(".headline ul", root).append(li); });
  $(".cols .card b", root).textContent = a.settings.controller;
  a.caveats.forEach((t) => { const li = el("li"); li.textContent = t; $("#caveats", root).append(li); });
  $("#toTrain", root).addEventListener("click", () => goStep(4));
  root.hidden = false;
}
async function startEval() {
  $("#evalcfg").hidden = true; $("#evalresult").hidden = true; $("#evalprogress").hidden = false;
  $("#chips").innerHTML = CONTROLLERS.map((c) => `<span class="chip" data-k="${c.key}">${c.name}</span>`).join("");
  $("#evalbar").style.width = "0"; $("#evaltext").textContent = "Starting…";
  let run;
  try { await ensureScenario(); run = await api("/api/evaluate", { body: { scenario_id: state.scenarioId, agent_id: state.agentId, episodes: state.evalRuns } }); }
  catch (e) { toast("Could not start the evaluation: " + e.message); $("#evalcfg").hidden = false; $("#evalprogress").hidden = true; return; }
  state.evalId = run.id; const began = Date.now();
  const tick = async () => {
    let r; try { r = await api("/api/evaluate/" + run.id); } catch (e) { clearInterval(state.evalPoll); toast(e.message); return; }
    if (r.state === "running") {
      $$("#chips .chip").forEach((c, i) => c.classList.toggle("on", i < r.finished));
      $("#evalbar").style.width = (r.finished / r.total) * 100 + "%";
      $("#evaltext").textContent = `${r.finished} of ${r.total} controllers finished · ${r.episodes} runs each · ${Math.round((Date.now() - began) / 1000)} s elapsed. You can leave this page open.`;
    } else {
      clearInterval(state.evalPoll); $("#evalprogress").hidden = true; $("#evalcfg").hidden = false;
      if (r.state === "done") renderResult(r); else toast("The evaluation failed: " + (r.message || "unknown error").split("\n").pop(), 9000);
    }
  };
  state.evalPoll = setInterval(tick, 1800); tick();
}
function evalEstimate() {
  const min = Math.max(1, Math.round((5 + state.evalRuns * 3 * 1.6) / 60));   // measured: ~1.6 s per run per controller
  $("#evaltime").textContent = `Takes about ${min} minute${min > 1 ? "s" : ""}. You can leave the page open.`;
}
function bindEval() {
  $("#runs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; state.evalRuns = +b.dataset.v; $$("#runs button").forEach((x) => x.classList.toggle("on", x === b)); evalEstimate(); });
  evalEstimate();
  $("#startEval").addEventListener("click", startEval);
}

/* ───────────── step 4: training ───────────── */
function trainEstimate() {
  const ep = +$("#tr-ep").value, sd = +$("#tr-seeds").value;
  $("#o-tr-ep").textContent = ep; $("#o-tr-seeds").textContent = sd;
  $("#tr-est").textContent = `About ${Math.round(sd * (ep * TRAIN_SECONDS_PER_EPISODE + TRAIN_SECONDS_PER_SEED) / 60)} minutes on a laptop.`;
}
function sparkline(vals) {
  if (!vals.length) return ""; const W = 900, H = 140, L = 10, T = 8, B = 8, lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
  const x = (i) => L + (W - 2 * L) * i / Math.max(vals.length - 1, 1), y = (v) => H - B - (H - T - B) * (v - lo) / span;
  return `<polyline fill="none" stroke="#2a78d6" stroke-width="2.4" stroke-linejoin="round" points="${vals.map((v, i) => x(i).toFixed(1) + "," + y(v).toFixed(1)).join(" ")}"/>`;
}
async function startTrain() {
  $("#traincfg").hidden = true; $("#trainresult").hidden = true; $("#trainprogress").hidden = false; $("#trtitle").textContent = "Training…";
  let job;
  try { await ensureScenario(); job = await api("/api/train", { body: { scenario_id: state.scenarioId, episodes: +$("#tr-ep").value, seeds: +$("#tr-seeds").value } }); }
  catch (e) { toast("Could not start training: " + e.message); $("#traincfg").hidden = false; $("#trainprogress").hidden = true; return; }
  state.trainId = job.id; $("#cancelTrain").disabled = false;
  const tick = async () => {
    let r; try { r = await api("/api/train/" + job.id); } catch (e) { clearInterval(state.trainPoll); toast(e.message); return; }
    const s = r.status, eps = Math.max(s.episodes || 1, 1), seeds = Math.max((s.seeds || []).length, 1);
    if (s.state === "queued" || s.state === "running") {
      const done = (s.seed_index || 0) * eps + (s.episode || 0); $("#trbar").style.width = Math.min(100, 100 * done / (seeds * eps)) + "%";
      $("#trtext").textContent = `${s.message || "Starting"} · ${s.stage || ""} · episode ${s.episode || 0} of ${eps}`; $("#trchart").innerHTML = sparkline(s.rewards || []);
    } else {
      clearInterval(state.trainPoll); $("#trainprogress").hidden = true; $("#traincfg").hidden = false;
      if (s.state === "done" && r.result) renderTrained(r);
      else if (s.state === "cancelled") toast("Training was cancelled. No agent was kept.");
      else toast("Training " + (s.state === "stalled" ? "stopped reporting" : "failed") + (s.message ? ": " + s.message : ""), 9000);
    }
  };
  state.trainPoll = setInterval(tick, 2000); tick();
}
function renderTrained(r) {
  const res = r.result, ref = res.reference_waiting, root = $("#trainresult");
  root.innerHTML = `<div class="card trainres"><h3>Training finished</h3>
    <table><tr><th>Trained seed</th><th class="n">Waiting on check runs</th></tr>
    ${res.seeds.map((s) => `<tr><td>${s.seed}${s.seed === res.chosen_seed ? " (chosen)" : ""}</td><td class="n">${num(s.mean_total_waiting)}</td></tr>`).join("")}
    <tr><td>Fixed timer, same runs</td><td class="n">${num(ref.fixed)}</td></tr><tr><td>Density rule, same runs</td><td class="n">${num(ref.rule)}</td></tr></table>
    <p class="hint" style="margin:10px 0"></p><button class="cta" id="useAgent">Use this agent in the comparison →</button></div>`;
  $(".hint", root).textContent = res.note; root.hidden = false;
  $("#useAgent", root).addEventListener("click", async () => { await loadAgents(r.agent_id); goStep(2); startCompare(); });
  loadAgents(r.agent_id);
}
function bindTrain() {
  ["#tr-ep", "#tr-seeds"].forEach((s) => $(s).addEventListener("input", trainEstimate)); trainEstimate();
  $("#startTrain").addEventListener("click", startTrain);
  $("#cancelTrain").addEventListener("click", async () => { try { await api(`/api/train/${state.trainId}/cancel`, { method: "POST" }); $("#cancelTrain").disabled = true; toast("Cancelling…"); } catch (e) { toast(e.message); } });
}

/* ───────────── start ───────────── */
bindTraffic(); bindCompare(); bindEval(); bindTrain(); buildTrio();
loadAgents().catch((e) => toast("Could not load the agents: " + e.message));
goStep(1);
