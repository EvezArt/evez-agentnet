from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator import (  # noqa: E402
    append_spine,
    load_state,
    run_generate,
    run_predict,
    run_scan,
    run_ship,
    save_state,
)

app = FastAPI(title="evez-agentnet", version="1.0.0")
API_KEY = os.environ.get("EVEZ_API_KEY") or os.environ.get("NEXT_PUBLIC_EVEZ_API_KEY", "")


class DispatchRequest(BaseModel):
    agent: str = "orchestrator"
    task: str = "run_cycle"
    payload: dict[str, Any] = {}


@app.get("/health")
def health() -> dict[str, Any]:
    state = load_state()
    return {
        "status": "ok",
        "service": "evez-agentnet",
        "time": datetime.now(timezone.utc).isoformat(),
        "round": state.get("round", 0),
        "total_earned_usd": state.get("total_earned_usd", 0.0),
    }


@app.get("/agents")
def agents() -> dict[str, Any]:
    state = load_state()
    return {
        "agents": state.get("agents", {}),
        "round": state.get("round", 0),
        "last_scan": state.get("last_scan"),
        "last_ship": state.get("last_ship"),
    }


@app.get("/skills")
def skills() -> dict[str, Any]:
    return {
        "id": "evez-agentnet",
        "capabilities": [
            "dispatch_task",
            "agent_status",
            "spawn_child",
            "agent_list",
        ],
        "auth_header": "X-EVEZ-API-KEY",
    }


@app.post("/dispatch")
def dispatch(req: DispatchRequest, x_evez_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    if API_KEY and x_evez_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    state = load_state()
    append_spine("dispatch_received", {"agent": req.agent, "task": req.task, "payload": req.payload})

    if req.task == "scan":
        scan_results = run_scan(state)
        save_state(state)
        return {"ok": True, "task": "scan", "count": len(scan_results), "results": scan_results[:10]}

    if req.task == "predict":
        scan_results = req.payload.get("scan_results", [])
        predictions = run_predict(scan_results, state)
        save_state(state)
        return {"ok": True, "task": "predict", "count": len(predictions), "results": predictions[:10]}

    if req.task == "generate":
        predictions = req.payload.get("predictions", [])
        drafts = run_generate(predictions, state)
        save_state(state)
        return {"ok": True, "task": "generate", "count": len(drafts), "results": drafts[:10]}

    if req.task == "ship":
        drafts = req.payload.get("drafts", [])
        earned = run_ship(drafts, state)
        save_state(state)
        return {"ok": True, "task": "ship", "earned_usd": earned}

    scan_results = run_scan(state)
    predictions = run_predict(scan_results, state)
    drafts = run_generate(predictions, state)
    earned = run_ship(drafts, state)
    state["round"] = state.get("round", 0) + 1
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    append_spine(
        "dispatch_complete",
        {
            "agent": req.agent,
            "task": req.task,
            "scan_count": len(scan_results),
            "prediction_count": len(predictions),
            "draft_count": len(drafts),
            "earned_usd": earned,
        },
    )
    return {
        "ok": True,
        "task": req.task,
        "scan_count": len(scan_results),
        "prediction_count": len(predictions),
        "draft_count": len(drafts),
        "earned_usd": earned,
    }
