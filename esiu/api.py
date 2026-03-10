#!/usr/bin/env python3
"""FastAPI surface for ESIU investigations."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from esiu.core import ESIU, Event

app = FastAPI(title="ESIU — Event Source Investigation Unit")
esiu = ESIU()


class EventRequest(BaseModel):
    kind: str = Field(..., examples=["auth.failure"])
    source: str = Field(..., examples=["192.168.1.1"])
    actor: str = Field(..., examples=["user_a"])
    subject: str = Field(..., examples=["login"])
    severity: int = Field(..., ge=0, le=100)
    metadata: dict = {}


@app.post("/investigate")
def investigate(req: EventRequest):
    event = Event(**req.model_dump())
    inv = esiu.investigate(event)
    return {
        "event_id": event.event_id,
        "verdict": inv.verdict,
        "action": inv.action_taken,
        "backtrace_n": len(inv.backtrace),
        "forward_n": len(inv.forward_impact),
        "requires_human": inv.action_taken == "QUEUED_FOR_HUMAN",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
