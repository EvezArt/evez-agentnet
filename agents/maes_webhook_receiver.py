"""
MAES Webhook Receiver
=====================
FastAPI endpoint that receives FIRE events from EVEZ-OS
and forwards them to MAES OracleBridge via POST /ingest.
Deploy alongside orchestrator.py.
"""

import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI(title="MAES Webhook Receiver")
MAES_URL = os.getenv("MAES_URL", "https://maes.railway.app")
client = httpx.AsyncClient(timeout=8)


@app.post("/webhook/fire")
async def receive_fire(request: Request):
    """Receive FIRE event from EVEZ-OS and forward to MAES oracle bridge."""
    payload = await request.json()
    try:
        r = await client.post(f"{MAES_URL}/oracle/ingest", json=payload)
        return {"forwarded": True, "maes_status": r.status_code}
    except Exception as e:
        return {"forwarded": False, "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok", "maes_url": MAES_URL}
