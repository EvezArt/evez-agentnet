#!/usr/bin/env python3
"""RuView live-surface recorder — turns the WiFi DensePose dashboard into recordings.

Opens the tailnet-bound RuView UI in headless Chrome, captures N seconds of the
live sensing surface via CDP, assembles an MP4 (ffmpeg), and saves a full-res
PNG still plus a JSON snapshot of /health, /api/v1/status, /api/v1/nodes and
/api/v1/mat/events. With --probe it injects manual ADR-018 probe frames
(node 254, the reserved manual-probe id) over UDP 5005 during capture so the
surface visibly reacts to real frames. Probes are opt-in, never the default,
per the ruview-tailnet skill law.

Usage:
  python3 record_ruview.py [--seconds 14] [--probe] [--out-dir DIR]

Requires: google-chrome, ffmpeg, websockets (python). Server must be up at
the Tailscale address (default 100.126.180.47:3000, container ruview-demo).
"""
import argparse
import base64
import datetime as dt
import json
import math
import os
import random
import socket
import struct
import subprocess
import sys
import time
import urllib.request

import websockets

SERVER = os.environ.get("RUVIEW_SERVER", "100.126.180.47")
HTTP_PORT = 3000
UDP_PORT = 5005
CDP_PORT = 9223
MAGIC = 0xC5110001
PROBE_NODE_ID = 254  # reserved manual-probe id (253 belongs to the watchdog)


def http(path, method="GET"):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (CDP_PORT, path), method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def api_token():
    out = subprocess.run(
        ["docker", "inspect", "ruview-demo", "--format", "{{range .Config.Env}}{{println .}}{{end}}"],
        capture_output=True, text=True, timeout=30).stdout
    for line in out.splitlines():
        if line.startswith("RUVIEW_API_TOKEN="):
            return line.split("=", 1)[1]
    return ""


def build_probe_frame(seq, t):
    """ADR-018 ESP32 CSI frame, manual probe node 254, breathing-paced amplitude."""
    n_ant, n_sub, freq = 2, 64, 2437
    p = bytearray()
    p += struct.pack("<I", MAGIC)
    p += struct.pack("<B", PROBE_NODE_ID)
    p += struct.pack("<B", n_ant)
    p += struct.pack("<H", n_sub)          # u16 at offset 6 — NOT a single byte
    p += struct.pack("<I", freq)
    p += struct.pack("<I", seq)
    p += struct.pack("<b", -60)            # rssi
    p += struct.pack("<b", -95)           # noise floor
    p += struct.pack("<B", 0)             # ppdu type
    p += struct.pack("<B", 0)             # flags
    amp = 40 + 30 * math.sin(2 * math.pi * 0.25 * t) + random.randint(-5, 5)
    for _ in range(n_ant * n_sub):
        p += struct.pack("<b", int(max(-127, min(127, amp * random.uniform(-1, 1)))))
        p += struct.pack("<b", int(max(-127, min(127, amp * random.uniform(-1, 1)))))
    return bytes(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=14.0)
    ap.add_argument("--probe", action="store_true",
                    help="inject manual probe frames (node 254) during capture")
    ap.add_argument("--out-dir", default="/root/evez-agentnet/forge_output/ruview_recordings")
    ap.add_argument("--url", default=None, help="override target URL (e.g. the tailscale serve address)")
    args = ap.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    mp4_path = os.path.join(out_dir, "ruview_live_%s%s.mp4" % (stamp, "_probe" if args.probe else ""))
    png_path = os.path.join(out_dir, "ruview_live_%s%s.png" % (stamp, "_probe" if args.probe else ""))
    json_path = os.path.join(out_dir, "ruview_snapshot_%s.json" % stamp)
    frames_dir = os.path.join(out_dir, ".frames_%s" % stamp)
    os.makedirs(frames_dir, exist_ok=True)

    token = api_token()
    print("api token present:", bool(token), "| server:", SERVER)

    url = args.url or ("http://%s:%d/ui/index.html" % (SERVER, HTTP_PORT))
    import urllib.parse as _up
    _host = _up.urlparse(url).hostname or ""
    chrome_args = ["google-chrome", "--headless=new",
                   "--remote-debugging-port=%d" % CDP_PORT,
                   "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                   "--no-first-run", "--user-data-dir=/tmp/ruview-rec-prof"]
    if _host.endswith(".ts.net"):
        # MagicDNS ts.net names may not resolve from the host itself; pin to the tailnet IP
        chrome_args.append("--host-resolver-rules=MAP %s %s" % (_host, SERVER))
    chrome_args.append("about:blank")
    chrome = subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sock = None
    try:
        for _ in range(20):
            try:
                http("/json/version")
                break
            except Exception:
                time.sleep(0.5)
        target = http("/json/new?" + url.replace("?", "%3F").replace("&", "%26"), "PUT")
        async def run():
            async with websockets.connect(target["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024) as ws:
                mid = [0]
                async def cmd(method, params=None):
                    mid[0] += 1
                    i = mid[0]
                    await ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
                    while True:
                        m = json.loads(await ws.recv())
                        if m.get("id") == i:
                            return m.get("result", {})
                await cmd("Runtime.enable")
                await cmd("Page.enable")
                await cmd("Emulation.setDeviceMetricsOverride",
                          {"width": 1600, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
                import asyncio
                await asyncio.sleep(3.0)
                # give the UI the bearer if it keeps one in localStorage
                if token:
                    for key in ("ruview-api-token", "ruview_token", "ruview_api_token", "token", "api_token"):
                        await cmd("Runtime.evaluate", {
                            "expression": "try{localStorage.setItem('%s','%s')}catch(e){}" % (key, token),
                            "returnByValue": True})
                await cmd("Page.reload", {"ignoreCache": True})
                await asyncio.sleep(6.0)
                # best-effort: jump to the live dashboard section
                await cmd("Runtime.evaluate", {
                    "expression": "try{var n=[].slice.call(document.querySelectorAll('nav a,a[href*=\"dashboard\"],button')).find(function(e){return /dashboard/i.test(e.textContent||'')});if(n){n.click()}}catch(e){}",
                    "returnByValue": True})
                await asyncio.sleep(2.0)
                state = await cmd("Runtime.evaluate", {
                    "expression": "document.body ? document.body.innerText.slice(0,600) : 'no body'",
                    "returnByValue": True})
                print("UI state text:", repr(state.get("result", {}).get("value", ""))[:600])

                if args.probe:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                n_frames = max(2, int(args.seconds / 0.4))
                print("capturing %d frames (~%.1fs)..." % (n_frames, args.seconds))
                seq = int(time.time())
                t0 = time.time()
                for i in range(n_frames):
                    if args.probe:
                        for _ in range(3):
                            seq += 1
                            sock.sendto(build_probe_frame(seq, time.time() - t0), (SERVER, UDP_PORT))
                    r = await cmd("Page.captureScreenshot", {"format": "png"})
                    with open(os.path.join(frames_dir, "%04d.png" % i), "wb") as f:
                        f.write(base64.b64decode(r["data"]))
                    await asyncio.sleep(0.35)
                if sock:
                    sock.close()
                print("frames captured:", n_frames)
        import asyncio
        asyncio.run(run())
        try:
            http("/json/close/" + target["id"])
        except Exception:
            pass  # /json/close answers with plain text on newer Chrome; non-fatal
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=8)
        except Exception:
            chrome.kill()

    # assemble the recording
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "2.5",
                     "-i", os.path.join(frames_dir, "%04d.png"),
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                     mp4_path], check=True)
    # full-res still = final frame
    last = sorted(os.listdir(frames_dir))[-1]
    with open(png_path, "wb") as out, open(os.path.join(frames_dir, last), "rb") as src:
        out.write(src.read())
    for f in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, f))
    os.rmdir(frames_dir)

    # data-side snapshot (the numbers behind the pixels)
    snap = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(), "server": SERVER}
    hdr = {"Authorization": "Bearer " + token}
    for name, path in (("health", "/health"), ("status", "/api/v1/status"),
                       ("nodes", "/api/v1/nodes"), ("mat_events", "/api/v1/mat/events")):
        try:
            req = urllib.request.Request("http://%s:%d%s" % (SERVER, HTTP_PORT, path), headers=hdr)
            snap[name] = json.loads(urllib.request.urlopen(req, timeout=10).read())
        except Exception as e:
            snap[name] = {"error": str(e)}
    with open(json_path, "w") as f:
        json.dump(snap, f, indent=1)

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                            "-show_entries", "stream=width,height,codec_name",
                            "-of", "json", mp4_path], capture_output=True, text=True)
    print("RECORDING:", mp4_path, os.path.getsize(mp4_path), "bytes")
    print("PROBE:", probe.stdout.strip()[:400])
    print("STILL:", png_path, os.path.getsize(png_path), "bytes")
    print("SNAPSHOT:", json_path, os.path.getsize(json_path), "bytes")
    print("NODES:", json.dumps(snap.get("nodes", {}))[:300])


if __name__ == "__main__":
    sys.exit(main())
