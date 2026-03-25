"""Vercel Serverless API Route — /api/pipeline
Deploys automatically on push to main via Vercel GitHub integration.
Postman collection target: evezart-285668.postman.co
"""
from http.server import BaseHTTPRequestHandler
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.agi_orchestrator import run_pipeline
from pipeline.sentry_instrument import init_sentry, trace_pipeline

init_sentry()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._run("EVEZ AGI pipeline health check — GET")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
            prompt = data.get("prompt", "EVEZ AGI pipeline POST test")
        except Exception:
            prompt = "EVEZ AGI pipeline POST test"
        self._run(prompt)

    @trace_pipeline("vercel/api/pipeline")
    def _run(self, prompt: str):
        result = run_pipeline(prompt)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-EVEZ-Run-ID", result["run_id"][:12])
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())
