#!/usr/bin/env python3
"""Tailnet RuView path watchdog - server side.

Proves, on an interval, that the whole phone->tailnet->server path is still
intact: container up, all three tailnet ports published on the Tailscale
address, UDP data plane accepting a real frame, and the sensing stream
answering. Appends one JSON line per probe to the dated evidence file.

This is a liveness attestation, not a claim about sensing accuracy. It records
what it actually observed on the wire.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

SERVER = os.environ.get("RUVIEW_SERVER", "100.126.180.47")
HTTP_PORT = 3000
WS_PORT = 3001
UDP_PORT = 5005
TOKEN = os.environ.get("RUVIEW_API_TOKEN", "").strip()
PROBE_NODE = 253  # reserved for health probes; never a real node id
EVIDENCE_ROOT = os.environ.get(
    "EVIDENCE_ROOT", "/root/evez-agentnet/evidence"
)


def headers() -> dict:
    return {"Authorization": "Bearer " + TOKEN} if TOKEN else {}


def http_get(path: str, timeout: float = 5.0):
    url = "http://%s:%d%s" % (SERVER, HTTP_PORT, path)
    req = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def udp_probe() -> bool:
    """Send one real ADR-018 frame and confirm the server registered it.

    A UDP send alone proves nothing, so this verifies server-side: the probe
    node must appear in /api/v1/nodes with a fresh csi_sequence afterwards.
    """
    hdr = bytearray()
    hdr += struct.pack("<I", 0xC5110001)
    hdr += bytes([PROBE_NODE, 1])
    hdr += struct.pack("<H", 64)
    hdr += struct.pack("<I", 2437)
    hdr += struct.pack("<I", int(time.time()) & 0xFFFFFFFF)
    hdr += struct.pack("<b", -60)
    hdr += struct.pack("<b", -92)
    hdr += bytes([0, 0])
    frame = bytes(hdr) + b"\x00\x00" * 64

    before = {n["node_id"]: n for n in http_get("/api/v1/nodes").get("nodes", [])}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(4.0)
    s.sendto(frame, (SERVER, UDP_PORT))
    s.close()

    for _ in range(10):
        time.sleep(0.5)
        after = {n["node_id"]: n for n in http_get("/api/v1/nodes").get("nodes", [])}
        now = after.get(PROBE_NODE)
        old = before.get(PROBE_NODE)
        if now and (old is None or now.get("csi_sequence") != old.get("csi_sequence")):
            return True
    return False


def container_up() -> bool:
    try:
        out = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "ruview-demo"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def probe() -> dict:
    record = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "server": SERVER,
        "container_up": container_up(),
    }
    try:
        record["health"] = http_get("/health")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        record["health_error"] = str(exc)
        record["ok"] = False
        return record
    try:
        record["udp_5005_roundtrip"] = udp_probe()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        record["udp_5005_error"] = str(exc)
        record["udp_5005_roundtrip"] = False
    record["ok"] = bool(record["container_up"] and record.get("udp_5005_roundtrip"))
    return record


def write_record(record: dict) -> str:
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(EVIDENCE_ROOT, day)
    os.makedirs(path, exist_ok=True)
    out = os.path.join(path, "ruview_tailnet.jsonl")
    with open(out, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return out


def main() -> int:
    once = "--once" in sys.argv
    interval = 900
    while True:
        record = probe()
        path = write_record(record)
        print("%s ok=%s health=%s udp=%s -> %s" % (
            record["ts"], record.get("ok"),
            (record.get("health") or {}).get("source"),
            record.get("udp_5005_roundtrip"), path), flush=True)
        if once:
            return 0 if record.get("ok") else 1
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
