"""
api/daemon.py — evez-agentnet
Vercel serverless entry point for the daemon.
One execution cycle per HTTP hit (Vercel cron every 5 min).
Resolves: evez-agentnet#15

Deploy: set GITHUB_TOKEN + OPENROUTER_API_KEY in Vercel env vars.
"""
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from daemon import issue_queue, spine
from daemon.loop import cycle


def handler(request, response=None):
    """Vercel Python handler."""
    try:
        issue_queue.ensure_labels()
        processed = cycle()
        body = {
            "status":    "ok",
            "processed": processed,
            "spine":     spine.count(),
            "recent":    spine.tail(5),
        }
        status = 200
    except Exception as e:
        body   = {"status": "error", "error": str(e)}
        status = 500

    if response is not None:
        response.status_code = status
        response.headers["Content-Type"] = "application/json"
        response.body = json.dumps(body)
        return response
    # WSGI / plain return
    return (status, {"Content-Type": "application/json"}, json.dumps(body))


# FastAPI compat (if uvicorn is used locally)
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.get("/api/daemon")
    @app.post("/api/daemon")
    async def daemon_endpoint():
        try:
            issue_queue.ensure_labels()
            processed = cycle()
            return JSONResponse({"status": "ok", "processed": processed,
                                  "spine": spine.count(), "recent": spine.tail(5)})
        except Exception as e:
            return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
except ImportError:
    pass
