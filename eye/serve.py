"""EVEZ EYE — refresh daemon.

Design constraint, learned the hard way: this process phones NOWHERE. It binds
127.0.0.1 only, makes no outbound requests, and serves exactly two files (the
generated HTML and the JSON behind it). An operator's own stack telemetry has
no business egressing, and a monitoring agent that does is the same bug class
as the credential leak this repo spent a day cleaning up.

Run:  python3 serve.py [--port 8900] [--interval 60]
"""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import collect                                    # noqa: E402
import render                                     # noqa: E402

TYPES = {".html": "text/html; charset=utf-8",
         ".json": "application/json; charset=utf-8"}


def refresh_loop(interval: int, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            data = collect.build()
            (ROOT / "data.json").write_text(json.dumps(data, indent=2))
            (ROOT / "index.html").write_text(render.render(data))
            print(f"[{time.strftime('%H:%M:%S')}] refreshed "
                  f"{data['generated']}", flush=True)
        except Exception as e:                    # never die on one bad cycle
            print(f"[{time.strftime('%H:%M:%S')}] refresh failed: {e}",
                  flush=True)
        stop.wait(interval)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt, *args):            # quiet by default
        pass

    def do_GET(self):
        path = self.path.split("?")[0].lstrip("/") or "index.html"
        # Strict allowlist. This daemon serves the eye and nothing else; a
        # path-traversal or SSRF surface here would be self-inflicted.
        if path not in ("index.html", "data.json"):
            self.send_error(404, "not found")
            return
        f = ROOT / path
        if not f.is_file():
            self.send_error(404, "not generated yet")
            return
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES[f.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # Local-only console: forbid embedding, and send a minimal CSP so a
        # future edit to index.html cannot introduce an outbound request.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--once", action="store_true",
                    help="refresh once, serve until interrupted")
    a = ap.parse_args()

    print(f"collecting initial snapshot…", flush=True)
    data = collect.build()
    (ROOT / "data.json").write_text(json.dumps(data, indent=2))
    (ROOT / "index.html").write_text(render.render(data))

    stop = threading.Event()
    if a.interval > 0:
        threading.Thread(target=refresh_loop,
                         args=(a.interval, stop), daemon=True).start()

    # Loopback only. Never 0.0.0.0 — an ops console is not a public service.
    with Server(("127.0.0.1", a.port), Handler) as httpd:
        print(f"EVEZ EYE → http://127.0.0.1:{a.port}/  "
              f"(loopback only, refresh {a.interval}s)", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            stop.set()
            print("\nstopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
