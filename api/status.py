"""
api/status.py — evez-agentnet
FastAPI single-file status endpoint.
Runs: uvicorn api.status:app --host 0.0.0.0 --port 8080
"""

import json
from pathlib import Path
from datetime import datetime, timezone

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    raise ImportError("pip install fastapi uvicorn")

from agents.accumulator import get_summary

STATE_PATH = Path("worldsim/worldsim_state.json")
SPINE_PATH = Path("spine/spine.jsonl")

app = FastAPI(title="evez-agentnet status", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def load_spine_tail(n: int = 20) -> list:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text().strip().split("\n")
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


@app.get("/status")
def status():
    state   = load_state()
    summary = get_summary()
    agents  = state.get("agents", {})
    return {
        "ok": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "round": state.get("round", 0),
        "total_earned_usd": state.get("total_earned_usd", 0.0),
        "accumulator": summary,
        "agents": {
            k: {
                "reputation":       round(v.get("reputation", 0), 3),
                "tasks_completed":  v.get("tasks_completed", 0),
                "streak":           v.get("streak", 0),
            }
            for k, v in agents.items()
        },
        "openclaw": state.get("openclaw", {}),
        "maes": state.get("maes", {}),
        "rsi_hypotheses": state.get("rsi", {}).get("hypotheses", []),
        "temporal_wormhole": state.get("temporal_wormhole", {}),
    }


@app.get("/spine")
def spine(n: int = 20):
    return {"entries": load_spine_tail(n)}


@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}
