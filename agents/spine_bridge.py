from __future__ import annotations

import os
from typing import Any

import httpx

EVEZ_OS_BASE = os.environ.get("EVEZ_OS_BASE", "").rstrip("/")
EVEZ_API_KEY = os.environ.get("EVEZ_API_KEY", "")


async def fire(
    event_name: str,
    source: str,
    data: dict[str, Any] | None = None,
    broadcast: bool = True,
    severity: str = "info",
) -> dict[str, Any]:
    payload = {
        "event_name": event_name,
        "source": source,
        "data": data or {},
        "broadcast": broadcast,
        "severity": severity,
    }
    if not EVEZ_OS_BASE:
        return {"ok": False, "reason": "missing EVEZ_OS_BASE", "payload": payload}

    headers = {"Content-Type": "application/json"}
    if EVEZ_API_KEY:
        headers["X-EVEZ-API-KEY"] = EVEZ_API_KEY

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{EVEZ_OS_BASE}/api/fire", json=payload, headers=headers)
        return {"ok": resp.is_success, "status_code": resp.status_code, "text": resp.text[:500]}


async def fire_task_complete(agent_id: str, task: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    return await fire(
        event_name="FIRE_TASK_COMPLETE",
        source=agent_id,
        data={"task": task, "result": result or {}},
        severity="info",
    )


async def fire_cain_escalate(agent_id: str, reason: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return await fire(
        event_name="FIRE_CAIN_ESCALATE",
        source=agent_id,
        data={"reason": reason, "context": context or {}},
        severity="high",
    )


async def fire_anomaly(agent_id: str, description: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return await fire(
        event_name="FIRE_ANOMALY",
        source=agent_id,
        data={"description": description, "data": data or {}},
        severity="medium",
    )
