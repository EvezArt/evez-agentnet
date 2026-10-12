#!/usr/bin/env python3
"""Static film server for the tailnet — loopback only, tailscale fronts it."""
import http.server, socketserver, os, sys
from pathlib import Path

ROOT = Path("/root/evez-agentnet/forge_output/films")
ALLOWED = {"the_hand_learns.mp4", "the_awakening.mp4", "the_siege_and_the_silence.mp4"}

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)
    def log_message(self, *a): pass
    def do_GET(self):
        name = self.path.split("?")[0].lstrip("/")
        if name not in ALLOWED:
            self.send_error(404, "not in the film registry")
            return
        f = ROOT / name
        if not f.is_file():
            self.send_error(404, "missing")
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(f.stat().st_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with f.open("rb") as fh:
            while chunk := fh.read(1 << 20):
                self.wfile.write(chunk)

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 8901), H) as srv:
    print("film server on 127.0.0.1:8901", flush=True)
    srv.serve_forever()
