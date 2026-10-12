"""Writes the project's design diagrams as draw.io (diagrams.net) files.

    python scripts/make_drawio_diagrams.py

Output: docs/diagrams/<name>.drawio  (open with https://app.diagrams.net or the desktop app,
edit freely, and export to PNG/SVG/PDF from File > Export as).

Names, methods and flows come from the code in traffic_drl/ (see the comments per diagram).
"""
import os
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "diagrams")

COL = {  # fill, stroke
    "blue": ("#dae8fc", "#6c8ebf"), "green": ("#d5e8d4", "#82b366"), "orange": ("#ffe6cc", "#d79b00"),
    "gray": ("#f5f5f5", "#666666"), "purple": ("#e1d5e7", "#9673a6"), "red": ("#f8cecc", "#b85450"),
    "yellow": ("#fff2cc", "#d6b656"), "white": ("#ffffff", "#333333"),
}


def sty(color="blue", extra="", font=13):
    f, s = COL[color]
    return f"whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize={font};{extra}"


class Dia:
    def __init__(self, name, w=1500, h=1000):
        self.name, self.w, self.h = name, w, h
        self.cells = []
        self.n = 1

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def v(self, x, y, w, h, text, style, parent="1"):
        i = self._id()
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(text, {chr(34): "&quot;"})}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def box(self, x, y, w, h, text, color="blue", extra="rounded=1;", font=13):
        return self.v(x, y, w, h, text, sty(color, extra, font))

    def label(self, x, y, w, h, text, font=13, extra="align=left;"):
        return self.v(x, y, w, h, text, f"text;html=1;whiteSpace=wrap;fontSize={font};verticalAlign=top;{extra}")

    def e(self, src, tgt, label="", style="", pts=None, sp=None, tp=None, dashed=False, arrow="block", start=None):
        i = self._id()
        base = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;fontSize=12;labelBackgroundColor=#ffffff;"
        hollow = arrow == "block_hollow"
        base += f"endArrow={'block' if hollow else arrow};endFill={0 if hollow else 1};"
        if start:
            base += f"startArrow={start};startFill=1;"
        if dashed:
            base += "dashed=1;"
        src_a = f' source="{src}"' if src else ""
        tgt_a = f' target="{tgt}"' if tgt else ""
        geo = '<mxGeometry relative="1" as="geometry">'
        if sp:
            geo += f'<mxPoint x="{sp[0]}" y="{sp[1]}" as="sourcePoint"/>'
        if tp:
            geo += f'<mxPoint x="{tp[0]}" y="{tp[1]}" as="targetPoint"/>'
        if pts:
            geo += "<Array as=\"points\">" + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in pts) + "</Array>"
        geo += "</mxGeometry>"
        self.cells.append(
            f'<mxCell id="{i}" value="{escape(label, {chr(34): "&quot;"})}" style="{base}{style}" edge="1" parent="1"{src_a}{tgt_a}>{geo}</mxCell>')
        return i

    def save(self):
        os.makedirs(OUT, exist_ok=True)
        xml = (f'<mxfile host="app.diagrams.net"><diagram id="{self.name}" name="{self.name}">'
               f'<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
               f'pageScale="1" pageWidth="{self.w}" pageHeight="{self.h}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
               + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>")
        path = os.path.join(OUT, f"{self.name}.drawio")
        open(path, "w", encoding="utf-8").write(xml)
        return path


def title(d, text, sub=""):
    d.label(30, 10, d.w - 60, 30, f"<b>{text}</b>", font=20, extra="align=left;")
    if sub:
        d.label(30, 42, d.w - 60, 24, sub, font=12, extra="align=left;fontColor=#666666;")


# ================================================================ 1. business context
def business_context():
    d = Dia("business-context", 1400, 860)
    title(d, "Business context: Adaptive Traffic Signal Control", "Who and what the system deals with. Goal: fewer vehicles waiting than with a fixed timer.")
    straight = "edgeStyle=none;"
    sysb = d.box(500, 300, 400, 200, "<b>Adaptive Traffic Signal Control System</b><br>(traffic_drl: package, CLI, demo app)<br><br>Learns a DQN signal controller and<br>compares it with a fixed-time controller", "blue", "rounded=1;strokeWidth=2;", 14)
    res = d.box(60, 90, 250, 90, "<b>Researcher / developer</b><br>configures, trains,<br>evaluates", "green")
    sup = d.box(60, 560, 250, 90, "<b>Supervisor / assessor</b><br>watches the demo,<br>reads the reports", "green")
    pla = d.box(1090, 90, 250, 100, "<b>Traffic agencies and<br>smart-city planners</b><br>(intended beneficiaries)", "orange", "rounded=1;dashed=1;")
    sumo = d.box(1090, 560, 250, 100, "<b>SUMO traffic simulator</b><br>(external, via TraCI)", "gray")
    cfg = d.box(525, 80, 350, 90, "<b>Intersection and scenario definitions</b><br>YAML configs, network and route XML", "yellow")
    git = d.box(525, 660, 350, 90, "<b>GitHub repository</b><br>code, configs, checkpoints, results", "gray")
    d.e(res, sysb, "commands: train, sweep, evaluate", style=straight + "exitX=1;exitY=0.9;entryX=0;entryY=0.05;")
    d.e(sysb, res, "metrics, plots, checkpoints", style=straight + "exitX=0;exitY=0.3;entryX=0.8;entryY=1;")
    d.e(sup, sysb, "asks for a demo", style=straight + "exitX=0.8;exitY=0;entryX=0;entryY=0.9;")
    d.e(sysb, sup, "live comparison, test results", style=straight + "exitX=0;exitY=0.98;entryX=1;entryY=0.35;")
    d.e(cfg, sysb, "configs and route files", style=straight)
    d.e(sysb, pla, "evidence: waiting time vs fixed timer", style=straight + "exitX=1;exitY=0.2;entryX=0;entryY=1;", dashed=True)
    d.e(sysb, sumo, "set signal phase", style=straight + "exitX=1;exitY=0.8;entryX=0;entryY=0.1;")
    d.e(sumo, sysb, "queues, waiting vehicles", style=straight + "exitX=0;exitY=0.7;entryX=1;entryY=0.98;")
    d.e(sysb, git, "push code and results", style=straight + "exitX=0.3;exitY=1;entryX=0.3;entryY=0;")
    d.e(git, sysb, "pull latest code", style=straight + "exitX=0.7;exitY=0;entryX=0.7;entryY=1;")
    d.box(60, 720, 380, 100, "<b>Aim</b><br>Show that an adaptive agent reduces congestion<br>(average vehicles waiting) compared with a fixed timer.", "white", "rounded=0;dashed=1;", 12)
    return d.save()


# ================================================================ 2. use case
def use_case():
    d = Dia("use-case", 1400, 960)
    title(d, "Use case diagram", "Actors and what they can do with traffic_drl (commands of the traffic-drl CLI and the demo app).")
    d.v(300, 80, 780, 840, "traffic_drl system", "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;verticalAlign=top;fontStyle=1;fontSize=14;")
    actor = "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fontSize=13;"
    r = d.v(100, 400, 40, 80, "Researcher", actor)
    s = d.v(1180, 220, 40, 80, "Supervisor (viewer)", actor)
    sm = d.v(1180, 700, 40, 80, "SUMO simulator<br>(secondary actor)", actor)
    uc = "ellipse;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
    L = [("Configure intersection<br>and scenarios", 110), ("Generate route files", 205), ("Check environment<br>(env-check)", 300),
         ("Train agent<br>(Q-table or DQN)", 395), ("Run hyperparameter<br>sweep", 490), ("Evaluate checkpoint<br>on fresh seeds", 585),
         ("Run fixed-time<br>baseline", 680), ("Plot training and<br>comparison charts", 775)]
    ids = {}
    for t, y in L:
        ids[t] = d.v(330, y, 250, 70, t, uc)
    live = d.v(720, 190, 270, 70, "Run live side-by-side demo", uc)
    view = d.v(890, 330, 180, 70, "View saved<br>test results", uc)
    sim = d.v(720, 640, 270, 80, "Simulate traffic<br>(SUMO via TraCI)", uc.replace("#dae8fc", "#ffe6cc").replace("#6c8ebf", "#d79b00"))
    line = "edgeStyle=none;"
    for t, y in L:
        d.e(r, ids[t], "", arrow="none", style=line + "exitX=1;exitY=0.3;entryX=0;entryY=0.5;")
    d.e(s, live, "", arrow="none", style=line + "entryX=1;entryY=0.5;")
    d.e(s, view, "", arrow="none", style=line + "entryX=1;entryY=0.5;")
    d.e(sim, sm, "", arrow="none", style=line + "exitX=1;exitY=0.5;")
    inc = "edgeStyle=none;dashed=1;"
    for t in ("Train agent<br>(Q-table or DQN)", "Evaluate checkpoint<br>on fresh seeds", "Run fixed-time<br>baseline"):
        d.e(ids[t], sim, "&lt;&lt;include&gt;&gt;", style=inc + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;", arrow="open")
    d.e(live, sim, "&lt;&lt;include&gt;&gt;", style=inc + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;", arrow="open")
    d.e(ids["Run hyperparameter<br>sweep"], ids["Train agent<br>(Q-table or DQN)"], "&lt;&lt;include&gt;&gt;", style=inc + "exitX=0.5;exitY=0;entryX=0.5;entryY=1;", arrow="open")
    return d.save()


# ================================================================ 3. class diagram
def cls(d, x, y, w, name, attrs, methods, color="blue", stereo=""):
    head = (f"<i>&lt;&lt;{stereo}&gt;&gt;</i><br>" if stereo else "") + f"<b>{name}</b>"
    body = head + "<hr>" + "<br>".join(attrs) + "<hr>" + "<br>".join(methods)
    lines = len(attrs) + len(methods) + (3 if stereo else 2)
    h = 22 + lines * 17
    return d.v(x, y, w, h, body, sty(color, "align=left;verticalAlign=top;spacing=6;spacingTop=2;", 12)), h


def class_diagram():
    d = Dia("class-diagram", 1650, 1180)
    title(d, "Class diagram (traffic_drl)", "Agents share one informal interface (act, decay_epsilon, save, load); DQNAgent owns the network, buffer and optimiser.")
    agent, _ = cls(d, 640, 70, 330, "Agent", [], ["act(state, greedy) : int", "decay_epsilon()", "save(path) / load(path)"], "gray", "interface")
    fx, _ = cls(d, 60, 250, 310, "FixedTimeAgent", ["green_steps : int", "n_actions : int"], ["act(state, greedy) : int", "reset()"], "green")
    qt, _ = cls(d, 430, 250, 380, "QTableAgent", ["queue_bins, alpha, gamma", "epsilon, q : dict", "n_actions : int"],
                ["discretize(state) : tuple", "act(state, greedy) : int", "update(s, a, r, s', done)", "decay_epsilon()", "save(path) / load(path)"], "green")
    dq, _ = cls(d, 880, 250, 440, "DQNAgent", ["online, target : MLP", "buffer : ReplayBuffer", "optimizer : Adam", "gamma, epsilon, batch_size", "target_sync_steps, loss"],
                ["from_config(config, state_dim)", "q_values(state) : ndarray", "act(state, greedy) : int", "update(s, a, r, s', done)", "learn() : float", "decay_epsilon()", "save(path) / load(path)"], "blue")
    mlp, _ = cls(d, 700, 700, 340, "MLP", ["sizes : list", "weights, biases"], ["forward(x) : ndarray", "backward(grad_out)", "copy_from(other)", "save(path) / load(path)"], "purple")
    rb, _ = cls(d, 1110, 700, 330, "ReplayBuffer", ["capacity : int", "state_dim : int"], ["add(s, a, r, s', done)", "sample(batch_size)", "__len__()"], "purple")
    ad, _ = cls(d, 1110, 930, 330, "Adam", ["lr, beta1, beta2, eps", "moment estimates"], ["step(dW, db)"], "purple")
    env, _ = cls(d, 60, 760, 450, "TraciEnv", ["config, scenarios, seed_base", "state_size, n_actions", "decision_interval, episode_length"],
                 ["reset() : state", "step(action) : (state, reward, done)", "metrics() : dict", "snapshot() : dict", "close()"], "orange")
    tr, _ = cls(d, 60, 480, 450, "training (module)", [], ["run_episode(env, agent, train)", "train_agent(env, agent, episodes, ...)", "evaluate(env, agent, episodes, seed_base)"], "yellow", "module")
    sw, _ = cls(d, 560, 480, 300, "sweep (module)", [], ["expand_grid(grid)", "run_sweep(env, config, grid, seeds)"], "yellow", "module")
    for a, ex in ((fx, 0.15), (qt, 0.5), (dq, 0.85)):
        d.e(a, agent, "", style=f"dashed=1;exitX=0.5;exitY=0;entryX={ex};entryY=1;", arrow="block_hollow")
    d.e(dq, mlp, "online + target", arrow="open", start="diamondThin", style="exitX=0.3;exitY=1;entryX=0.7;entryY=0;")
    d.e(dq, rb, "", arrow="open", start="diamondThin", style="exitX=0.8;exitY=1;entryX=0.5;entryY=0;")
    d.e(dq, ad, "uses", arrow="open", dashed=True, style="exitX=1;exitY=0.7;entryX=1;entryY=0.5;")
    d.e(tr, agent, "drives", dashed=True, arrow="open", style="exitX=0;exitY=0.2;entryX=0;entryY=0.5;", pts=[(25, 506), (25, 125)])
    d.e(tr, env, "uses", dashed=True, arrow="open")
    d.e(sw, tr, "calls", dashed=True, arrow="open")
    return d.save()


# ================================================================ 4. data flow
def data_flow():
    d = Dia("data-flow-diagram", 1500, 1060)
    title(d, "Data flow diagram (level 1)", "Processes (circles), external entities (boxes) and data stores (open boxes).")
    ent = "rounded=0;"
    proc = "ellipse;"
    store = "shape=partialRectangle;whiteSpace=wrap;html=1;left=0;right=0;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;"
    res = d.box(40, 90, 150, 70, "<b>Researcher</b>", "green", ent)
    sumo = d.box(40, 330, 150, 70, "<b>SUMO simulator</b>", "gray", ent)
    sup = d.box(640, 890, 150, 70, "<b>Supervisor</b>", "green", ent)
    p1 = d.box(300, 70, 210, 110, "<b>1.0</b><br>Load configuration<br>and scenarios", "blue", proc)
    p2 = d.box(300, 310, 210, 110, "<b>2.0</b><br>Simulate traffic<br>and sense state", "blue", proc)
    p3 = d.box(640, 310, 210, 110, "<b>3.0</b><br>Select action<br>(agent)", "blue", proc)
    p4 = d.box(640, 540, 210, 110, "<b>4.0</b><br>Compute reward<br>and learn", "blue", proc)
    p5 = d.box(300, 540, 210, 110, "<b>5.0</b><br>Record metrics<br>and evaluate", "blue", proc)
    p6 = d.box(300, 860, 210, 110, "<b>6.0</b><br>Plot, compare<br>and demo", "blue", proc)
    d1 = d.v(620, 95, 250, 60, "D1  Config files (YAML, net, routes)", store)
    d2 = d.v(980, 565, 240, 60, "D2  Replay buffer", store)
    d3 = d.v(300, 740, 210, 60, "D3  Checkpoints (.npz)", store)
    d4 = d.v(40, 565, 190, 60, "D4  Results (CSV)", store)
    d.e(res, p1, "config choices, commands")
    d.e(d1, p1, "settings, scenarios")
    d.e(p1, p2, "scenario, seed")
    d.e(p2, sumo, "set phase", style="exitX=0;exitY=0.3;entryX=1;entryY=0.3;")
    d.e(sumo, p2, "queues, waiting, arrivals", style="exitX=1;exitY=0.7;entryX=0;entryY=0.7;")
    d.e(p2, p3, "state vector", style="exitX=1;exitY=0.3;entryX=0;entryY=0.3;")
    d.e(p3, p2, "action (keep / switch)", style="exitX=0;exitY=0.7;entryX=1;entryY=0.7;")
    d.e(p2, p4, "transition (s, a, r, s')", style="exitX=0.9;exitY=1;entryX=0.2;entryY=0;", pts=[(489, 490), (682, 490)])
    d.e(p4, p3, "updated weights", style="exitX=0.8;exitY=0;entryX=0.8;entryY=1;")
    d.e(p4, d2, "transitions", style="exitX=1;exitY=0.4;entryX=0;entryY=0.4;")
    d.e(d2, p4, "minibatch", style="exitX=0;exitY=0.8;entryX=1;entryY=0.7;")
    d.e(p4, d3, "best weights", style="exitX=0.3;exitY=1;entryX=1;entryY=0.5;", pts=[(703, 770)])
    d.e(p2, p5, "episode metrics")
    d.e(d3, p5, "checkpoint to evaluate")
    d.e(p5, d4, "per-episode results", style="exitX=0;exitY=0.5;entryX=1;entryY=0.5;")
    d.e(d4, p6, "results", style="exitX=0.5;exitY=1;entryX=0;entryY=0.6;", pts=[(135, 926)])
    d.e(p6, sup, "charts, live comparison")
    d.e(p6, res, "charts, tables", pts=[(15, 880), (15, 125)], style="exitX=0;exitY=0.18;entryX=0;entryY=0.5;")
    return d.save()


# ================================================================ 5. ER diagram
def er_diagram():
    d = Dia("er-diagram", 1700, 1200)
    title(d, "Entity-relationship diagram", "The data the system stores: YAML configs, route files, checkpoints (.npz) and result CSVs. PK = key, FK = reference.")

    def ent(x, y, w, name, attrs, color="blue"):
        body = f"<b>{name}</b><hr>" + "<br>".join(attrs)
        h = 34 + 17 * len(attrs)
        return d.v(x, y, w, h, body, sty(color, "align=left;verticalAlign=top;spacing=6;rounded=0;", 12))

    cfg = ent(60, 80, 330, "INTERSECTION_CONFIG", ["PK name", "network_file, route_file, sumocfg_file", "traffic_light_id", "step_length, episode_length", "decision_interval, yellow_duration", "state_features, reward weights", "dqn hyperparameters"], "orange")
    app = ent(60, 380, 330, "APPROACH", ["PK approach_id", "FK config_name", "name (east, north, west, south)", "incoming_edge"], "orange")
    ph = ent(60, 560, 330, "PHASE", ["PK phase_index", "FK config_name", "name (north_south_green, ...)"], "orange")
    sc = ent(480, 80, 320, "SCENARIO", ["PK scenario_name", "FK config_name (extends)", "description", "route_file", "vehicles_per_hour profile"], "yellow")
    sw = ent(900, 80, 320, "SWEEP", ["PK sweep_id", "grid (setting -> values)", "seeds", "episodes, eval_episodes", "out_dir"], "green")
    run = ent(900, 380, 340, "TRAINING_RUN", ["PK run_id", "FK sweep_id (optional)", "FK config_name", "agent_type (qtable, dqn)", "setting (lr, gamma, decay, penalty)", "seed, episodes"], "blue")
    log = ent(1310, 380, 330, "EPISODE_LOG", ["PK (run_id, episode)", "reward, epsilon, loss", "mean_total_waiting", "throughput_per_hour", "switches"], "purple")
    ck = ent(900, 640, 340, "CHECKPOINT", ["PK checkpoint_path (.npz)", "FK run_id", "hidden_sizes, state_dim", "best_episode"], "purple")
    ev = ent(900, 880, 380, "EVALUATION_RESULT", ["PK eval_id", "FK checkpoint_path (null = fixed-time)", "FK scenario_name", "seed_base, episode", "mean_total_waiting, mean_queue", "mean_backlog, avg_wait_per_vehicle", "throughput_per_hour, switches", "ns_green_fraction"], "purple")
    one_many = "startArrow=ERmandOne;endArrow=ERmany;startFill=0;endFill=0;"
    def rel(a, b, lab, extra="", pts=None):
        d.e(a, b, lab, style=one_many + extra, pts=pts)
    rel(cfg, app, "has", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    rel(cfg, ph, "has", "exitX=0;exitY=0.9;entryX=0;entryY=0.5;", pts=[(30, 218), (30, 610)])
    rel(cfg, sc, "is extended by", "exitX=1;exitY=0.3;entryX=0;entryY=0.5;")
    rel(sw, run, "contains", "exitX=0.8;exitY=1;entryX=0.8;entryY=0;")
    rel(cfg, run, "configures", "exitX=0.9;exitY=1;entryX=0.2;entryY=0;", pts=[(357, 300), (968, 300)])
    rel(run, log, "records", "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    rel(run, ck, "saves", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    rel(ck, ev, "is evaluated in", "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    rel(sc, ev, "is used in", "exitX=0.5;exitY=1;entryX=0;entryY=0.5;", pts=[(640, 960)])
    return d.save()


# ================================================================ 6. functional architecture
def functional_architecture():
    d = Dia("functional-architecture", 1500, 1100)
    title(d, "Functional architecture", "Functions grouped in layers; each layer uses the one below.")

    def band(y, h, name, color):
        f, s = COL[color]
        d.v(30, y, 1440, h, name, f"rounded=0;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};opacity=40;verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;fontSize=14;")

    def fn(x, y, w, h, text, color):
        return d.box(x, y, w, h, text, color, "rounded=1;", 12)

    def down(y):
        d.e(None, None, "", style="edgeStyle=none;endArrow=block;strokeWidth=3;strokeColor=#888888;", sp=(750, y), tp=(750, y + 28))

    band(80, 150, "1. Interface", "green")
    fn(60, 120, 620, 95, "<b>Command-line tool (traffic-drl)</b><br>env-check, train, sweep, baseline, evaluate,<br>plot, run (streams JSON lines), demo", "green")
    fn(760, 120, 680, 95, "<b>Streamlit demo app</b><br>live side-by-side run, junction drawing, counters and chart,<br>saved test results, how it works", "green")
    band(260, 180, "2. Experiments", "yellow")
    fn(60, 305, 440, 110, "<b>Training and evaluation loop</b><br>episodes, epsilon schedule, periodic greedy<br>evaluation on unseen seeds, best checkpoint", "yellow")
    fn(530, 305, 420, 110, "<b>Hyperparameter sweep</b><br>grid x seeds, per-run results, ranking,<br>resume after interruption", "yellow")
    fn(980, 305, 460, 110, "<b>Configuration and scenarios</b><br>YAML with inheritance, scenario list,<br>route generator (tidal, rush hour, low traffic)", "yellow")
    band(470, 220, "3. Controllers and learning components", "blue")
    fn(60, 515, 280, 150, "<b>DQN agent</b><br>epsilon-greedy act, learn from minibatch,<br>target-network sync", "blue")
    fn(365, 515, 220, 150, "<b>Q-table agent</b><br>bucketed state,<br>tabular update", "blue")
    fn(610, 515, 220, 150, "<b>Fixed-time controller</b><br>40 s green per direction,<br>no learning", "blue")
    fn(855, 515, 300, 150, "<b>Neural network library</b><br>MLP, backpropagation, Adam,<br>Huber / MSE loss", "purple")
    fn(1180, 515, 260, 150, "<b>Replay buffer</b><br>stored transitions,<br>random minibatches", "purple")
    band(720, 190, "4. Simulation environment (TraciEnv)", "orange")
    fn(60, 765, 270, 120, "<b>State sensing</b><br>queues, waiting time, phase,<br>time in phase, backlog", "orange")
    fn(355, 765, 270, 120, "<b>Action execution</b><br>switch phase, insert 3 s yellow,<br>5 s decision interval", "orange")
    fn(650, 765, 270, 120, "<b>Reward accounting</b><br>cost every simulated second,<br>switch penalty, scale", "orange")
    fn(945, 765, 240, 120, "<b>Metrics</b><br>waiting, throughput,<br>switches", "orange")
    fn(1210, 765, 230, 120, "<b>Seeds and scenarios</b><br>per-episode seed,<br>scenario cycling", "orange")
    band(940, 100, "5. Supporting: simulator and analysis", "gray")
    fn(60, 975, 560, 50, "<b>SUMO simulator, controlled through TraCI</b>", "gray")
    fn(660, 975, 780, 50, "<b>Analysis and visualisation:</b> training curves, comparison charts and tables (matplotlib)", "gray")
    for y in (232, 442, 692, 912):
        down(y)
    return d.save()


# ================================================================ 7. system architecture
def system_architecture():
    d = Dia("system-architecture", 1600, 1000)
    title(d, "System architecture (deployment)", "Where each part runs: development on a Mac, real simulations and the demo on a Windows laptop, code shared through GitHub.")
    d.v(30, 80, 1060, 850, "Windows laptop (real simulations and demo)", "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#6c8ebf;verticalAlign=top;fontStyle=1;fontSize=14;dashed=1;arcSize=3;")
    d.v(1150, 80, 430, 280, "Mac (development)", "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#82b366;verticalAlign=top;fontStyle=1;fontSize=14;dashed=1;arcSize=3;")
    br = d.box(80, 130, 240, 90, "<b>Web browser</b><br>demo page (localhost:8501)", "green")
    st = d.box(440, 130, 320, 90, "<b>Streamlit server</b><br>traffic_drl/app.py<br>starts and polls the runs", "blue")
    rf = d.box(100, 300, 300, 90, "<b>traffic-drl run</b> (fixed-time)<br>one process per controller", "blue")
    rd = d.box(460, 300, 300, 90, "<b>traffic-drl run</b> (DQN)<br>loads checkpoint .npz", "blue")
    jl = d.box(100, 470, 660, 70, "<b>fixed.jsonl and dqn.jsonl</b> (temporary folder)<br>one JSON line per decision: queues, signal, counters", "yellow")
    s1 = d.box(100, 640, 300, 80, "<b>SUMO</b> instance (eclipse-sumo)<br>headless, fixed-time run", "gray")
    s2 = d.box(460, 640, 300, 80, "<b>SUMO</b> instance (eclipse-sumo)<br>headless, DQN run", "gray")
    fs = d.box(60, 790, 980, 100, "<b>Project files</b><br>configs/ (YAML, net, routes)   checkpoints/*.npz   figures/*.csv   results_sweep_*/<br>Python 3.12 virtual environment with the traffic_drl package", "yellow")
    dev = d.box(1180, 140, 370, 120, "<b>traffic_drl package</b> + tests<br>unit tests with a fake TraCI,<br>demo preview with a fake simulator", "green")
    gh = d.box(1190, 470, 350, 150, "<b>GitHub repository (main)</b><br>code, configs, tests, checkpoints,<br>figures, sweep results, docs", "gray")
    d.e(br, st, "HTTP", arrow="block", start="block", style="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    d.e(st, rf, "starts process", style="exitX=0.2;exitY=1;entryX=0.5;entryY=0;")
    d.e(st, rd, "starts process", style="exitX=0.8;exitY=1;entryX=0.5;entryY=0;")
    d.e(rf, jl, "writes", style="exitX=0.5;exitY=1;entryX=0.2;entryY=0;")
    d.e(rd, jl, "writes", style="exitX=0.5;exitY=1;entryX=0.8;entryY=0;")
    d.e(jl, st, "polled every 0.15 s", dashed=True, style="exitX=1;exitY=0.5;entryX=1;entryY=0.5;", pts=[(900, 505), (900, 175)])
    d.e(rf, s1, "TraCI (local socket)", arrow="block", start="block", style="exitX=0;exitY=0.5;entryX=0;entryY=0.5;", pts=[(55, 345), (55, 680)])
    d.e(rd, s2, "TraCI (local socket)", arrow="block", start="block", style="exitX=1;exitY=0.5;entryX=1;entryY=0.5;", pts=[(815, 345), (815, 680)])
    d.e(dev, gh, "git push / pull", arrow="block", start="block", style="exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    d.e(gh, fs, "git pull / push", arrow="block", start="block", style="exitX=0;exitY=0.5;entryX=1;entryY=0.5;", pts=[(1120, 545), (1120, 840)])
    return d.save()


# ================================================================ 8. sequence diagram
def sequence_diagram():
    d = Dia("sequence-diagram", 1500, 1100)
    title(d, "Sequence diagram: one training run (traffic-drl train --agent dqn)", "Loop over episodes; inside each, a loop over decisions every 5 simulated seconds.")
    names = ["Researcher", "CLI (cli.py)", "Trainer (training.py)", "TraciEnv", "SUMO (TraCI)", "DQNAgent"]
    xs = [60, 300, 540, 800, 1030, 1270]
    ll = "shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;outlineConnect=0;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=13;"
    cx = {}
    for n, x in zip(names, xs):
        d.v(x, 80, 150, 40, n, ll)
        d.cells[-1] = d.cells[-1].replace('height="40"', 'height="980"')
        cx[n] = x + 75
    # frames first so messages draw on top
    frame = "shape=umlFrame;whiteSpace=wrap;html=1;width=160;height=26;fontSize=12;fillColor=none;strokeColor=#888888;"
    d.v(500, 300, 880, 650, "loop [episodes]", frame)
    d.v(520, 450, 840, 330, "loop [each decision, 5 s]", frame)
    d.v(520, 820, 840, 110, "alt [every eval_every episodes]", frame)
    msgs = [
        ("Researcher", "CLI (cli.py)", 150, "traffic-drl train --agent dqn", False),
        ("CLI (cli.py)", "Trainer (training.py)", 190, "train_agent(env, agent, episodes)", False),
        ("Trainer (training.py)", "TraciEnv", 340, "reset()", False),
        ("TraciEnv", "SUMO (TraCI)", 370, "traci.start(--seed, --route-files)", False),
        ("TraciEnv", "Trainer (training.py)", 410, "initial state", True),
        ("Trainer (training.py)", "DQNAgent", 490, "act(state)", False),
        ("DQNAgent", "Trainer (training.py)", 520, "action (epsilon-greedy)", True),
        ("Trainer (training.py)", "TraciEnv", 560, "step(action)", False),
        ("TraciEnv", "SUMO (TraCI)", 595, "setPhase (yellow first if switching)", False),
        ("TraciEnv", "SUMO (TraCI)", 630, "simulationStep() x 5, read queues each second", False),
        ("SUMO (TraCI)", "TraciEnv", 660, "queues, waiting, arrivals", True),
        ("TraciEnv", "Trainer (training.py)", 695, "next state, reward, done", True),
        ("Trainer (training.py)", "DQNAgent", 735, "update(s, a, r, s', done): store, learn, sync target", False),
        ("Trainer (training.py)", "DQNAgent", 800, "decay_epsilon()", False),
        ("Trainer (training.py)", "TraciEnv", 855, "evaluate(): greedy runs on unseen seeds", False),
        ("Trainer (training.py)", "DQNAgent", 900, "save(best.npz) if better", False),
        ("Trainer (training.py)", "CLI (cli.py)", 990, "reward history", True),
        ("CLI (cli.py)", "Researcher", 1030, "reward CSV and checkpoint", True),
    ]
    for a, b, y, text, ret in msgs:
        style = "html=1;verticalAlign=bottom;endArrow=block;fontSize=12;" + ("dashed=1;endArrow=open;" if ret else "")
        d.e(None, None, text, style="edgeStyle=none;" + style, sp=(cx[a], y), tp=(cx[b], y))
    return d.save()


# ================================================================ 9. activity diagram
def activity_diagram():
    d = Dia("activity-diagram", 1100, 1700)
    title(d, "Activity diagram: one training run", "Control flow of train_agent: episodes, decisions, learning and periodic evaluation.")
    act = lambda x, y, w, t, c="blue": d.box(x, y, w, 56, t, c, "rounded=1;arcSize=30;", 12)
    dec = lambda x, y, t: d.v(x, y, 260, 80, t, "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;")
    cxm = 450
    s = d.v(cxm - 15, 80, 30, 30, "", "ellipse;html=1;fillColor=#000000;strokeColor=#000000;")
    a1 = act(cxm - 160, 130, 320, "Load config, create environment and agent")
    a2 = act(cxm - 160, 215, 320, "Reset episode: next scenario and seed, start SUMO")
    a3 = act(cxm - 160, 300, 320, "Observe state (queues, waiting, phase, time in phase)")
    d1 = dec(cxm - 130, 385, "random &lt; epsilon?")
    a4a = act(60, 500, 240, "Explore: random action", "green")
    a4b = act(600, 500, 260, "Exploit: action with highest Q-value", "green")
    a5 = act(cxm - 160, 600, 320, "Apply action: keep green or switch (insert 3 s yellow)")
    a6 = act(cxm - 160, 685, 320, "Advance SUMO 5 s, add the cost every second")
    a7 = act(cxm - 160, 770, 320, "Compute reward, store transition in buffer")
    d2 = dec(cxm - 130, 855, "buffer has enough transitions?")
    a8 = act(620, 960, 300, "Learn: sample minibatch, update network, sync target every N steps", "purple")
    d3 = dec(cxm - 130, 1060, "episode over (30 simulated min)?")
    a9 = act(cxm - 160, 1170, 320, "Decay epsilon, log episode metrics")
    d4 = dec(cxm - 130, 1255, "evaluate this episode?")
    a10 = act(620, 1345, 300, "Greedy evaluation on unseen seeds; save checkpoint if best", "purple")
    d5 = dec(cxm - 130, 1430, "more episodes?")
    a11 = act(cxm - 160, 1545, 320, "Save final model and training log")
    e = d.v(cxm - 18, 1630, 36, 36, "", "ellipse;html=1;shape=endState;fillColor=#000000;strokeColor=#000000;")
    d.e(s, a1); d.e(a1, a2); d.e(a2, a3); d.e(a3, d1)
    d.e(d1, a4a, "yes", style="exitX=0;exitY=0.5;entryX=0.5;entryY=0;")
    d.e(d1, a4b, "no", style="exitX=1;exitY=0.5;entryX=0.5;entryY=0;")
    d.e(a4a, a5, "", style="exitX=0.5;exitY=1;entryX=0;entryY=0.5;")
    d.e(a4b, a5, "", style="exitX=0.5;exitY=1;entryX=1;entryY=0.5;")
    d.e(a5, a6); d.e(a6, a7); d.e(a7, d2)
    d.e(d2, a8, "yes", style="exitX=1;exitY=0.5;entryX=0.5;entryY=0;")
    d.e(d2, d3, "no")
    d.e(a8, d3, "", style="exitX=0.5;exitY=1;entryX=1;entryY=0.5;")
    d.e(d3, a3, "no", style="exitX=0;exitY=0.5;entryX=0;entryY=0.5;", pts=[(150, 1100), (150, 328)])
    d.e(d3, a9, "yes")
    d.e(a9, d4)
    d.e(d4, a10, "yes", style="exitX=1;exitY=0.5;entryX=0.5;entryY=0;")
    d.e(d4, d5, "no")
    d.e(a10, d5, "", style="exitX=0.5;exitY=1;entryX=1;entryY=0.5;")
    d.e(d5, a2, "yes", style="exitX=0;exitY=0.5;entryX=0;entryY=0.5;", pts=[(70, 1470), (70, 243)])
    d.e(d5, a11, "no")
    d.e(a11, e)
    return d.save()


# ================================================================ 10. workflow
def workflow_diagram():
    d = Dia("workflow-diagram", 2250, 560)
    title(d, "Workflow: from idea to a result we trust", "The experiment loop used in this project. Checkpoints are chosen on one set of seeds and confirmed on fresh seeds.")
    def step(i, text, color="blue"):
        return d.box(int(30 + i * 240), 120, 200, 100, text, color, "rounded=1;", 12)
    s1 = step(0, "<b>1. Define</b><br>scenario and config<br>(YAML, routes)", "yellow")
    s2 = step(1, "<b>2. Check</b><br>env-check on SUMO,<br>run the tests", "yellow")
    s3 = step(2, "<b>3. Train</b><br>Q-table warm-up,<br>then DQN")
    s4 = step(3, "<b>4. Tune</b><br>sweep: settings x seeds,<br>look at switches too")
    s5 = step(4, "<b>5. Select</b><br>best checkpoint on<br>selection seeds")
    s6 = step(5, "<b>6. Confirm</b><br>evaluate on fresh seeds<br>(10 episodes)", "green")
    dc = d.v(30 + 6 * 240 - 30, 90, 260, 160, "Better than (or tied with) the fixed timer?", "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;")
    s7 = step(7.1, "<b>7. Publish</b><br>plot, copy model to<br>checkpoints/, write up", "green")
    s8 = step(8.1, "<b>8. Demo</b><br>side-by-side app,<br>results tab", "green")
    base = d.box(30 + 5 * 240, 330, 200, 90, "<b>Fixed-time baseline</b><br>same seeds, same scenario", "gray", "rounded=1;", 12)
    dg = d.box(30 + 6 * 240, 330, 200, 120, "<b>Diagnose</b><br>check switches, backlog,<br>reward design;<br>change setting or design", "red", "rounded=1;", 12)
    for a, b in ((s1, s2), (s2, s3), (s3, s4), (s4, s5), (s5, s6), (s6, dc)):
        d.e(a, b)
    d.e(dc, s7, "yes", style="exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
    d.e(s7, s8)
    d.e(base, s6, "", style="exitX=0.5;exitY=0;entryX=0.5;entryY=1;")
    d.e(dc, dg, "no", style="exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
    d.e(dg, s3, "try again", style="exitX=0.5;exitY=1;entryX=0.5;entryY=1;", pts=[(30 + 6 * 240 + 100, 500), (30 + 2 * 240 + 100, 500)], dashed=True)
    return d.save()


if __name__ == "__main__":
    for fn in (business_context, use_case, class_diagram, data_flow, er_diagram, functional_architecture,
               system_architecture, sequence_diagram, activity_diagram, workflow_diagram):
        print("wrote", fn())
