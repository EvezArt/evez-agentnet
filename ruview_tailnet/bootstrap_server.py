#!/usr/bin/env python3
"""Tailnet bootstrap file server + phone registry (server side).

Two jobs, one process, bound to the Tailscale address only:

1. GET  /ruview_relay.py, /ruview_install.sh, /bootstrap.sh
   The phone fetches its own installer over the tailnet, so provisioning is one
   paste in Termux instead of a file transfer.

2. POST /register {"lan_ip": "..."}
   The relay reports the phone's LAN IP on the sensing WiFi. That IP is what
   the ESP32 must target, and it is otherwise unknowable from the server —
   it is a private RFC1918 address on a network the server cannot see. Having
   the phone self-report means the ESP32 target is never a value someone has to
   read off a screen and retype.

Security: bearer-gated and bound to 100.126.180.47, so only tailnet peers with
the token can read files or register an address. Registration is advisory data
for an operator decision — it never changes a firewall rule or points the
server anywhere by itself.
"""

from __future__ import annotations

import json
import os
import time
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BIND = os.environ.get("BIND_ADDR", "100.126.180.47")
PORT = int(os.environ.get("PORT", "8099"))
TOKEN = os.environ.get("RUVIEW_API_TOKEN", "").strip()
ROOT = os.environ.get("SERVE_ROOT", "/root/ruview")
REGISTRY = os.environ.get("REGISTRY", "/root/ruview/phone_registry.json")
LOG = os.environ.get("REGISTRY_LOG", "/root/ruview/phone_registry.jsonl")

FILES = {
    "/ruview_relay.py": "android/ruview_relay.py",
    "/ruview_install.sh": "android/ruview_install.sh",
    "/bootstrap.sh": "bootstrap_phone.sh",
}


def authorized(headers) -> bool:
    if not TOKEN:
        return True
    got = headers.get("Authorization", "")
    return got.strip() == "Bearer " + TOKEN


class Handler(BaseHTTPRequestHandler):
    server_version = "ruview-bootstrap/1.0"

    def log_message(self, fmt, *args):
        pass

    def _deny(self):
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":"unauthorized"}')

    def do_GET(self):
        if not authorized(self.headers):
            return self._deny()
        if self.path == "/health":
            body = json.dumps({"ok": True, "files": sorted(FILES)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if self.path == "/registry":
            try:
                with open(REGISTRY) as fh:
                    body = fh.read().encode()
            except FileNotFoundError:
                body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        rel = FILES.get(self.path)
        if not rel:
            self.send_response(404)
            self.end_headers()
            return
        full = os.path.join(ROOT, rel)
        try:
            with open(full, "rb") as fh:
                body = fh.read()
        except OSError:
            self.send_response(404)
            self.end_headers()
            return
        ctype = "text/x-shellscript" if full.endswith(".sh") else "text/x-python"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not authorized(self.headers):
            return self._deny()
        if self.path != "/register":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            lan_ip = str(payload.get("lan_ip", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self.send_response(400)
            self.end_headers()
            return self.wfile.write(b'{"error":"bad json"}')
        # Only a private IPv4 is meaningful here, and only as an operator hint.
        parts = lan_ip.split(".")
        if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            self.send_response(400)
            self.end_headers()
            return self.wfile.write(b'{"error":"bad lan_ip"}')
        if not (lan_ip.startswith("192.168.") or lan_ip.startswith("10.")
                or lan_ip.startswith("172.")):
            self.send_response(400)
            self.end_headers()
            return self.wfile.write(b'{"error":"not a private address"}')

        record = {
            "lan_ip": lan_ip,
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "reported_by": payload.get("hostname", ""),
            "tailscale_ip": payload.get("tailscale_ip", ""),
        }
        try:
            with open(REGISTRY) as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
        data[lan_ip] = record
        tmp = REGISTRY + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp, REGISTRY)
        with open(LOG, "a") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

        body = json.dumps({"ok": True, "esp32_target": lan_ip + ":5005"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print("ruview bootstrap server on %s:%d serving %s" % (BIND, PORT, sorted(FILES)), flush=True)
    srv.serve_forever()
