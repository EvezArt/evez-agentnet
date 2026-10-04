#!/usr/bin/env python3
"""RuView tailnet relay - Android/Termux side.

Purpose
-------
An ESP32 CSI node can only reach the RuView sensing server over the tailnet if
something on the phone's own WiFi network forwards its UDP frames. Phones do
not expose CSI to apps, and they do not run the ESP32 firmware; the phone's job
is to be the bridge:

    ESP32 --(UDP 5005, phone LAN IP)--> phone relay --(tailnet)--> VPS:5005

The relay is deliberately dumb about payloads. It never parses, rewrites, or
synthesises a frame - it reads a datagram and writes the identical bytes. Any
frame the ESP32 sends reaches the server byte-for-byte, and the server's
ADR-018 parser plus source allowlist stay the only authorities on what is real.

It also probes the sensing path so the phone can confirm reachability without a
browser.

Usage (Termux):
    pkg install python
    python ruview_relay.py --status
    python ruview_relay.py --relay --server 100.126.180.47
    python ruview_relay.py --relay --server 100.126.180.47 --bind 0.0.0.0:5005
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
import urllib.error
import urllib.request

ESP32_MAGIC = 0xC5110001
ESP32_HEADER_LEN = 20
DEFAULT_SERVER = "100.126.180.47"
DEFAULT_BIND = "0.0.0.0:5005"
SERVER_PORT = 5005
HTTP_PORT = 3000
TOKEN = os.environ.get("RUVIEW_API_TOKEN", "").strip()
LOG_EVERY = 50


def log(msg: str) -> None:
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def _headers() -> dict:
    return {"Authorization": "Bearer " + TOKEN} if TOKEN else {}


def http_get(server: str, path: str, timeout: float = 5.0):
    url = "http://%s:%d%s" % (server, HTTP_PORT, path)
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def build_esp32_frame(node_id: int, n_subcarriers: int, sequence: int) -> bytes:
    """Build a minimal, correctly-framed ESP32 CSI datagram.

    Layout is fixed by the firmware and mirrored in the server's
    `parse_esp32_frame` (ADR-018):
      [0..3] magic, [4] node, [5] antennas, [6..7] subcarriers u16,
      [8..11] freq u32, [12..15] sequence u32, [16] rssi i8,
      [17] noise i8, [18] PPDU, [19] flags, [20..] I/Q pairs.
    """
    hdr = bytearray()
    hdr += struct.pack("<I", ESP32_MAGIC)
    hdr += bytes([node_id & 0xFF, 1])
    hdr += struct.pack("<H", n_subcarriers)
    hdr += struct.pack("<I", 2437)
    hdr += struct.pack("<I", sequence)
    hdr += struct.pack("<b", -60)
    hdr += struct.pack("<b", -92)
    hdr += bytes([0, 0])
    body = bytearray()
    for _ in range(n_subcarriers):
        body += struct.pack("<bb", 0, 0)
    return bytes(hdr) + bytes(body)


def cmd_status(server: str, inject_probe: bool = False) -> int:
    """Prove the tailnet path end to end from the phone."""
    ok = True
    try:
        health = http_get(server, "/health")
        print("  health    : %s" % health)
        if health.get("source") == "simulated":
            print("  NOTE      : server is serving SIMULATED data - no live CSI node yet")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print("  health    : FAIL (%s)" % exc)
        ok = False

    try:
        nodes = http_get(server, "/api/v1/nodes")
        print("  nodes     : %s" % nodes)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print("  nodes     : FAIL (%s)" % exc)
        ok = False

    # UDP is connectionless: a successful send proves only that the local stack
    # emitted a datagram and nothing rejected it locally. It cannot confirm the
    # server received it. Proving that requires injecting a real ESP32 frame,
    # which would flip the server's source to "live" and register a phantom
    # node - so it is opt-in via --inject-probe, never the default. The honest
    # default signal is the server's own view in /health and /api/v1/nodes.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(4.0)
        s.sendto(b"", (server, SERVER_PORT))
        s.close()
        print("  udp 5005  : send OK (unverified delivery - UDP is connectionless)")
    except OSError as exc:
        print("  udp 5005  : FAIL (%s)" % exc)
        ok = False

    if inject_probe:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(4.0)
            s.sendto(build_esp32_frame(254, 64, int(time.time()) & 0xFFFFFFFF), (server, SERVER_PORT))
            s.close()
            time.sleep(1.5)
            after = http_get(server, "/health")
            print("  injected  : probe node 254 delivered (server source=%s)" % after.get("source"))
        except OSError as exc:
            print("  injected  : FAIL (%s)" % exc)
            ok = False

    print("  RESULT    :", "TAILNET PATH OK" if ok else "TAILNET PATH BROKEN")
    return 0 if ok else 1


def parse_addr(value: str):
    host, _, port = value.rpartition(":")
    if not host:
        raise ValueError("expected HOST:PORT, got %r" % value)
    return host.strip("[]"), int(port)


def cmd_relay(server: str, bind: str, duration) -> int:
    """Forward CSI frames from the local WiFi to the tailnet, unmodified."""
    bind_host, bind_port = parse_addr(bind)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    rx.bind((bind_host, bind_port))
    log("listening for ESP32 frames on %s:%d (LAN)" % (bind_host, bind_port))
    log("forwarding to %s:%d over Tailscale" % (server, SERVER_PORT))

    deadline = (time.time() + duration) if duration else None
    forwarded = 0
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_report = time.time()
    while True:
        if deadline and time.time() >= deadline:
            break
        rx.settimeout(1.0)
        try:
            data, peer = rx.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError as exc:
            log("recv error: %s" % exc)
            time.sleep(0.5)
            continue

        if len(data) < ESP32_HEADER_LEN:
            log("drop short datagram (%dB) from %s" % (len(data), peer[0]))
            continue
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic != ESP32_MAGIC:
            log("drop non-ESP32 magic 0x%08X from %s" % (magic, peer[0]))
            continue

        try:
            tx.sendto(data, (server, SERVER_PORT))
        except OSError as exc:
            log("forward failed to %s:%d: %s" % (server, SERVER_PORT, exc))
            time.sleep(1.0)
            continue

        forwarded += 1
        if forwarded % LOG_EVERY == 0:
            node = data[4]
            n_sub = struct.unpack_from("<H", data, 6)[0]
            now = time.time()
            rate = LOG_EVERY / max(now - last_report, 1e-6)
            log("forwarded %d frames (%.1f fps) node=%d subcarriers=%d" % (forwarded, rate, node, n_sub))
            last_report = now

    log("relay stopped after %d frames" % forwarded)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="RuView tailnet relay (Android/Termux)")
    ap.add_argument("--server", default=DEFAULT_SERVER, help="tailnet host of the sensing server")
    ap.add_argument("--relay", action="store_true", help="run the UDP forwarder")
    ap.add_argument("--status", action="store_true", help="probe the tailnet path and exit")
    ap.add_argument("--bind", default=DEFAULT_BIND, help="local listen address (default %(default)s)")
    ap.add_argument("--seconds", type=int, default=None, help="stop relay after N seconds")
    ap.add_argument(
        "--inject-probe",
        action="store_true",
        help="send one real ESP32 frame to prove the server received it "
        "(flips /health to esp32 and registers a probe node - diagnostic only)",
    )
    args = ap.parse_args(argv)

    if args.relay:
        return cmd_relay(args.server, args.bind, args.seconds)
    return cmd_status(args.server, args.inject_probe)


if __name__ == "__main__":
    sys.exit(main())
