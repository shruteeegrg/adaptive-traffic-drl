"""Web API for the client application (FastAPI). Every heavy job runs in its own process, so the server stays responsive:

  POST /api/preview            validate traffic as the client edits it (no files), returns load + advisories
  POST /api/scenario           build the scenario files for the traffic, returns a scenario id
  GET  /api/agents             trained agents the client can play with (generalist, specialists, their own)
  POST /api/compare            start the three controllers live on a scenario;   GET /api/compare/{id}?since=..  poll events
  POST /api/evaluate           statistical evaluation + recommendation + report;  GET /api/evaluate/{id}  poll / result
  GET  /api/evaluate/{id}/report.html
  POST /api/train              start a training job;  GET /api/train/{id};  POST /api/train/{id}/cancel

The front end (static/) talks only to this API. Bound to localhost by default: this is a single-user local tool,
not a multi-tenant service (no accounts, no isolation between users).
"""

import json
import re
import subprocess
import sys
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from traffic_drl import demo_core as core
from traffic_drl import intake
from traffic_drl import training_job as tj

STATIC = Path(__file__).with_name("static")
ID = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")
SPEEDS = {"slow": 0.12, "normal": 0.05, "fast": 0.01}


class Traffic(BaseModel):
    rates: dict = Field(default_factory=dict)          # {"east": veh/h, "north": ..., "west": ..., "south": ...}
    minutes: float = 30
    swap: bool = False
    mix_pct: dict = Field(default_factory=dict)         # {"motorcycle": %, "car": %, "bus": %, "goods": %}
    turns_pct: dict = Field(default_factory=dict)       # {"left": %, "right": %}


class CompareIn(BaseModel):
    scenario_id: str
    agent_id: str = "generalist"
    seed: int = 40000
    speed: str = "normal"


class EvaluateIn(BaseModel):
    scenario_id: str
    agent_id: str = "generalist"
    episodes: int = 30


class TrainIn(BaseModel):
    scenario_id: str
    episodes: int = tj.DEFAULT_EPISODES
    seeds: int = len(tj.DEFAULT_SEEDS)


def _safe(identifier: str) -> str:
    if not ID.match(identifier or ""):
        raise HTTPException(400, "bad id")
    return identifier


def _spec(t: Traffic, name: str = "my_junction") -> dict:
    rates = {a: float(t.rates.get(a, 0) or 0) for a in intake.APPROACHES}
    return core.custom_spec(name, rates, t.minutes, t.swap, t.mix_pct, t.turns_pct)


def create_app() -> FastAPI:
    runs = {}        # compare id -> {"files": {key: (jsonl, err)}, "procs": {key: Popen}}

    @asynccontextmanager
    async def lifespan(_app):
        yield
        for run in runs.values():       # do not leave simulations running after the server stops
            stop(run)

    app = FastAPI(title="Signal Studio", docs_url=None, redoc_url=None, lifespan=lifespan)
    lock = threading.Lock()
    evals = {}       # evaluate id -> {"dir": Path, "proc": Popen, "episodes": int}

    def web_dir(*parts) -> Path:
        d = tj.workspace().joinpath("web", *parts)
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------ traffic
    @app.post("/api/preview")
    def preview(t: Traffic):
        try:
            return intake.preview(_spec(t))
        except intake.SpecError as e:
            return JSONResponse({"error": str(e)}, status_code=422)

    @app.post("/api/scenario")
    def scenario(t: Traffic):
        sid = uuid.uuid4().hex[:10]
        d = web_dir("scenarios", sid)
        spec = _spec(t)
        try:
            built = intake.build_scenario(spec, str(d))
        except intake.SpecError as e:
            return JSONResponse({"error": str(e)}, status_code=422)
        (d / "spec.yaml").write_text(yaml.safe_dump(spec, sort_keys=False))
        (d / "context.json").write_text(json.dumps(built["context"]))
        return {"id": sid, "summary": built["summary"], "advisories": built["advisories"]}

    def scenario_dir(sid: str) -> Path:
        d = tj.workspace() / "web" / "scenarios" / _safe(sid)
        if not (d / "spec.yaml").exists():
            raise HTTPException(404, "unknown scenario")
        return d

    # ------------------------------------------------------------------- agents
    def agents() -> list:
        out = []
        if (core.ROOT / core.GENERALIST).exists():
            out.append({"id": "generalist", "label": "Generalist agent",
                        "note": "Trained on 12 random demand patterns; not on your exact traffic.",
                        "path": core.GENERALIST})
        jobs = tj.workspace() / "jobs"
        if jobs.exists():
            for r in sorted(jobs.glob("*/result.json"), reverse=True):
                out.insert(0, {"id": f"job:{r.parent.name}", "label": f"Trained on your traffic ({r.parent.name})",
                               "note": "Trained here, on the traffic you built. Not tested until you evaluate it.",
                               "path": str(r.parent / "model.npz")})
        try:
            manifest = json.loads((core.ROOT / "models" / "manifest.json").read_text())["models"]
        except (OSError, ValueError, KeyError):
            manifest = {}
        for key, m in manifest.items():
            if (core.ROOT / m["default"]).exists():
                out.append({"id": f"model:{key}", "label": f"Specialist: {key}",
                            "note": f"Trained for {Path(m['scenario']).stem if '/' in m['scenario'] else m['scenario']}.",
                            "path": m["default"]})
        return out

    def agent_path(agent_id: str) -> str:
        for a in agents():
            if a["id"] == agent_id:
                return a["path"]
        raise HTTPException(404, "unknown agent")

    @app.get("/api/agents")
    def agent_list():
        return {"agents": [{k: v for k, v in a.items() if k != "path"} for a in agents()]}

    # ------------------------------------------------------------------ compare
    def stop(run):
        for p in run["procs"].values():
            if p.poll() is None:
                p.terminate()

    @app.post("/api/compare")
    def compare_start(c: CompareIn):
        d = scenario_dir(c.scenario_id)
        checkpoint = agent_path(c.agent_id)
        rid = uuid.uuid4().hex[:10]
        out = web_dir("compare", rid)
        files, procs = {}, {}
        with lock:
            for old in runs.values():
                stop(old)
            for key in core.KEYS:
                files[key] = (str(out / f"{key}.jsonl"), str(out / f"{key}.err"))
                cmd = core.build_run_command(key, str(d / "my_junction.yaml"), checkpoint, c.seed,
                                             SPEEDS.get(c.speed, SPEEDS["normal"]), files[key][0])
                procs[key] = core.launch(cmd, files[key][1])
            runs[rid] = {"files": files, "procs": procs}
        return {"id": rid}

    @app.get("/api/compare/{rid}")
    def compare_poll(rid: str, fixed: int = 0, rule: int = 0, dqn: int = 0):
        run = runs.get(_safe(rid))
        if not run:
            raise HTTPException(404, "unknown run")
        since = {"fixed": fixed, "rule": rule, "dqn": dqn}
        events, counts, done, failed = {}, {}, True, None
        for key in core.KEYS:
            path, err = run["files"][key]
            all_events, _ = core.read_new_events(path, 0)
            events[key], counts[key] = all_events[since[key]:], len(all_events)
            finished = any(e.get("event") == "done" for e in all_events)
            done = done and finished
            code = run["procs"][key].poll()
            if code not in (None, 0) and not finished and not failed:
                failed = core.tail(err) or "the simulation could not start"
        return {"events": events, "counts": counts, "done": done, "failed": failed}

    # ----------------------------------------------------------------- evaluate
    @app.post("/api/evaluate")
    def evaluate_start(e: EvaluateIn):
        d = scenario_dir(e.scenario_id)
        checkpoint = agent_path(e.agent_id)
        episodes = min(max(int(e.episodes), 5), 200)
        eid = uuid.uuid4().hex[:10]
        out = web_dir("evals", eid)
        cmd = [sys.executable, "-m", "traffic_drl.cli", "advise", "--spec", str(d / "spec.yaml"),
               "--episodes", str(episodes), "--out-dir", str(out / "out"),
               "--dqn", f"dqn={checkpoint}@{core.ROOT / core.config_for(checkpoint)}"]
        proc = subprocess.Popen(cmd, cwd=str(core.ROOT), stdout=open(out / "job.log", "w"), stderr=subprocess.STDOUT)
        evals[eid] = {"dir": out, "proc": proc, "episodes": episodes}
        return {"id": eid}

    @app.get("/api/evaluate/{eid}")
    def evaluate_poll(eid: str):
        ev = evals.get(_safe(eid))
        if not ev:
            raise HTTPException(404, "unknown evaluation")
        log = (ev["dir"] / "job.log").read_text() if (ev["dir"] / "job.log").exists() else ""
        finished = log.count(" done (")
        code = ev["proc"].poll()
        advice_path = ev["dir"] / "out" / "advice.json"
        if code is None:
            return {"state": "running", "finished": finished, "total": 3, "episodes": ev["episodes"]}
        if code == 0 and advice_path.exists():
            advice = json.loads(advice_path.read_text())
            advice.pop("table_markdown", None)
            return {"state": "done", "advice": advice, "report_url": f"/api/evaluate/{eid}/report.html"}
        return {"state": "failed", "message": "\n".join(log.strip().splitlines()[-6:])}

    @app.get("/api/evaluate/{eid}/report.html")
    def evaluate_report(eid: str):
        path = tj.workspace() / "web" / "evals" / _safe(eid) / "out" / "report.html"
        if not path.exists():
            raise HTTPException(404, "report not ready")
        return FileResponse(path, media_type="text/html",
                            headers={"Content-Disposition": 'inline; filename="signal_timing_report.html"'})

    # -------------------------------------------------------------------- train
    @app.post("/api/train")
    def train_start(t: TrainIn):
        d = scenario_dir(t.scenario_id)
        episodes = min(max(int(t.episodes), 2), 300)
        job_dir, _ = tj.start_job(str(d / "my_junction.yaml"), name="my_junction", episodes=episodes,
                                  seeds=tuple(range(min(max(int(t.seeds), 1), 6))))
        return {"id": Path(job_dir).name, "estimate_minutes": tj.estimate_minutes(episodes, t.seeds)}

    @app.get("/api/train/{jid}")
    def train_poll(jid: str):
        d = tj.workspace() / "jobs" / _safe(jid)
        if not d.exists():
            raise HTTPException(404, "unknown job")
        status = tj.read_status(str(d))
        out = {"status": status}
        if status.get("state") == "done" and (d / "result.json").exists():
            out["result"] = json.loads((d / "result.json").read_text())
            out["agent_id"] = f"job:{jid}"
        return out

    @app.post("/api/train/{jid}/cancel")
    def train_cancel(jid: str):
        d = tj.workspace() / "jobs" / _safe(jid)
        if not d.exists():
            raise HTTPException(404, "unknown job")
        tj.request_cancel(str(d))
        return {"ok": True}

    # ------------------------------------------------------------------- static
    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    return app


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    import uvicorn

    if open_browser:
        import webbrowser

        threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
