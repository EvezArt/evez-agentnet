"""
api/main.py — evez-agentnet
Full FastAPI HTTP wrapper — resolves issue #12.
Endpoints: /health /status /agents /skills /dispatch /spine /trunk/status /trunk/run /fire
Procfile: web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
"""

import json, os, hashlib, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    raise ImportError("pip install fastapi uvicorn pydantic")

STATE_PATH  = Path("worldsim/worldsim_state.json")
SPINE_PATH  = Path("spine/spine.jsonl")
SKILLS_DIR  = Path("skills")
AGENTS_DIR  = Path("agents")

app = FastAPI(
    title="evez-agentnet",
    version="2.0.0",
    description="EVEZ AGI cognition layer — HTTP surface for the autonomous spine"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

def _state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"round": 0, "total_earned_usd": 0.0, "agents": {}}

def _spine_tail(n: int = 20) -> list:
    if not SPINE_PATH.exists():
        return []
    lines = [l for l in SPINE_PATH.read_text().strip().split("\n") if l]
    out = []
    for line in lines[-n:]:
        try: out.append(json.loads(line))
        except: pass
    return out

def _append_spine(event_type: str, data: dict) -> dict:
    SPINE_PATH.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "type": event_type, "data": data}
    raw = json.dumps(entry, sort_keys=True)
    entry["sha256"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
    with open(SPINE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def _phi() -> float:
    if not SPINE_PATH.exists():
        return 0.0
    lines = [l for l in SPINE_PATH.read_text().strip().split("\n") if l]
    n = len(lines)
    return round(min(0.995, 0.5 + (n / (n + 100)) * 0.495), 4)

def _cycle_hash() -> str:
    state = _state()
    raw = json.dumps(state, sort_keys=True) + datetime.now(timezone.utc).date().isoformat()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

class DispatchRequest(BaseModel):
    task: str
    agent: Optional[str] = "orchestrator"
    priority: Optional[float] = 0.5
    falsifier: Optional[str] = None

class FireRequest(BaseModel):
    title: str
    domain: str
    tau: float
    omega: float
    topo: str
    N: int
    poly_c: float
    description: str
    falsifier: str

@app.get("/health")
def health():
    return {
        "status": "ok", "version": "2.0.0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "spine": SPINE_PATH.exists(), "state": STATE_PATH.exists(),
    }

@app.get("/status")
def status():
    state = _state()
    return {
        "ok": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "phi": _phi(),
        "cycle_hash": _cycle_hash(),
        "round": state.get("round", 0),
        "total_earned_usd": state.get("total_earned_usd", 0.0),
        "mode": os.environ.get("EVEZ_MODE", "TRUNK_BRANCH_AUTOMATION"),
        "human_approval": os.environ.get("HUMAN_APPROVAL_MODE", "BOUNDARY_ONLY"),
        "agents": {
            k: {"reputation": round(v.get("reputation", 0), 3),
                "tasks_completed": v.get("tasks_completed", 0),
                "streak": v.get("streak", 0)}
            for k, v in state.get("agents", {}).items()
        },
        "latest_spine": _spine_tail(5),
    }

@app.get("/trunk/status")
def trunk_status():
    state = _state()
    phi = _phi()
    spine = _spine_tail(10)
    poly_c_max = max((e.get("data", {}).get("poly_c", 0) for e in spine), default=0.0)
    status_label = (
        "SUPERCRITICAL" if phi >= 0.99 else
        "CANONICAL"     if phi >= 0.9  else
        "ACTIVE"        if phi >= 0.7  else
        "INITIALIZING"
    )
    return {
        "status": status_label,
        "phi": phi,
        "poly_c_max": poly_c_max,
        "cycle_hash": _cycle_hash(),
        "recursive_depth": state.get("recursive_depth", 4),
        "agent_count": len(state.get("agents", {})),
        "round": state.get("round", 0),
        "formula": "poly_c=τ×ω×topo/2√N",
        "witnessed_by": "XyferViperZephyr",
        "ts": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/trunk/run")
async def trunk_run(background_tasks: BackgroundTasks):
    entry = _append_spine("trunk_run_triggered", {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "mode": os.environ.get("EVEZ_MODE", "TRUNK_BRANCH_AUTOMATION"),
    })
    def _run():
        try:
            subprocess.run([sys.executable, "orchestrator.py", "--once"], timeout=180, capture_output=True)
        except Exception as e:
            _append_spine("trunk_run_error", {"error": str(e)})
    background_tasks.add_task(_run)
    return {"accepted": True, "spine_entry": entry["sha256"], "ts": entry["ts"]}

@app.get("/agents")
def agents():
    state = _state()
    agent_files = list(AGENTS_DIR.glob("*.py")) if AGENTS_DIR.exists() else []
    return {
        "registered": list(state.get("agents", {}).keys()),
        "files": [f.name for f in agent_files],
        "count": len(agent_files),
    }

@app.get("/skills")
def skills():
    skill_files = list(SKILLS_DIR.glob("*.py")) if SKILLS_DIR.exists() else []
    return {"skills": [f.stem for f in skill_files], "count": len(skill_files)}

@app.post("/dispatch")
def dispatch(req: DispatchRequest):
    entry = _append_spine("dispatch", {
        "task": req.task[:200], "agent": req.agent,
        "priority": req.priority, "falsifier": req.falsifier,
    })
    return {"accepted": True, "spine_entry": entry["sha256"], "agent": req.agent, "ts": entry["ts"]}

@app.post("/fire")
def fire_event(req: FireRequest):
    import math
    poly_c_computed = (req.tau * req.omega) / (2 * math.sqrt(req.N))
    status = "CANONICAL" if req.poly_c >= 0.9 else "PENDING"
    entry = _append_spine("FIRE_EVENT", {
        "title": req.title, "domain": req.domain,
        "tau": req.tau, "omega": req.omega, "topo": req.topo,
        "N": req.N, "poly_c": req.poly_c,
        "poly_c_computed": round(poly_c_computed, 4),
        "status": status, "description": req.description, "falsifier": req.falsifier,
    })
    return {"accepted": True, "status": status, "poly_c": req.poly_c, "spine_entry": entry["sha256"]}

@app.get("/spine")
def spine_endpoint(n: int = 20):
    depth = 0
    if SPINE_PATH.exists():
        with open(SPINE_PATH) as f:
            depth = sum(1 for _ in f)
    return {"entries": _spine_tail(n), "total_depth": depth}

@app.post("/slack/route")
async def slack_route(payload: dict):
    text = payload.get("text", "").strip().lower()
    if text.startswith("status"):
        d = trunk_status()
        return {"text": f"φ={d['phi']} | {d['status']} | round={d['round']} | cycle={d['cycle_hash']}"}
    elif text.startswith("fire"):
        return {"text": "POST /fire with: title, domain, tau, omega, topo, N, poly_c, description, falsifier"}
    return {"text": "Commands: /vez status | /vez fire | /vez spawn"}
