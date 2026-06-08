#!/usr/bin/env python3
"""
honeypot/watcher.py  —  EVEZ-OS VCL Honeypot Watcher
Ingests YouTube livestream chat + network-level probes,
classifies actors via NPC engine, outputs public naughty list JSON.

Pipeline:
  YT Live Chat → chat_collector()
  Network Probes → net_collector()
  → npc_classifier.classify()
  → naughty_list.json  (public Vercel endpoint)
  → Ably spine channel evez-honeypot
"""

import os
import json
import socket
import hashlib
import datetime
import threading
import http.server
import urllib.request
from typing import Optional
from npc_classifier import NPCClassifier

ABLY_KEY = os.environ.get("ABLY_API_KEY", "")
YT_API_KEY = os.environ.get("YT_API_KEY", "")
LIVECHAT_ID = os.environ.get("YT_LIVECHAT_ID", "")   # populated from stream
HONEYPOT_PORT = int(os.environ.get("HONEYPOT_PORT", "18666"))
NAUGHTY_LIST_PATH = "output/naughty_list.json"

classifier = NPCClassifier()


# ──────────────────────────────────────────
# 1. YOUTUBE CHAT COLLECTOR
# ──────────────────────────────────────────

def get_livechat_messages(page_token: Optional[str] = None) -> tuple[list[dict], str]:
    """Poll YouTube Live Chat API for recent messages."""
    if not YT_API_KEY or not LIVECHAT_ID:
        return [], ""
    url = (
        f"https://www.googleapis.com/youtube/v3/liveChat/messages"
        f"?liveChatId={LIVECHAT_ID}&part=snippet,authorDetails&key={YT_API_KEY}"
        f"{'&pageToken=' + page_token if page_token else ''}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        messages = [
            {
                "source": "yt_chat",
                "author": item["authorDetails"]["displayName"],
                "author_id": item["authorDetails"]["channelId"],
                "is_verified": item["authorDetails"]["isVerified"],
                "is_chat_moderator": item["authorDetails"]["isChatModerator"],
                "is_chat_sponsor": item["authorDetails"]["isChatSponsor"],
                "text": item["snippet"]["displayMessage"],
                "published_at": item["snippet"]["publishedAt"],
            }
            for item in data.get("items", [])
        ]
        return messages, data.get("nextPageToken", "")
    except Exception as e:
        print(f"[watcher] YT chat error: {e}")
        return [], ""


# ──────────────────────────────────────────
# 2. NETWORK HONEYPOT LISTENER
# ──────────────────────────────────────────

class HoneypotHandler(http.server.BaseHTTPRequestHandler):
    """Low-interaction honeypot on HONEYPOT_PORT.
    Any inbound connection = potential probe. Log + classify."""

    def log_message(self, format, *args):
        pass  # suppress default logging

    def _record_probe(self):
        probe = {
            "source": "network_probe",
            "remote_addr": self.client_address[0],
            "method": self.command,
            "path": self.path,
            "user_agent": self.headers.get("User-Agent", ""),
            "host_header": self.headers.get("Host", ""),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        }
        # Classify immediately
        npc = classifier.classify(probe)
        if npc["tier"] != "clean":
            emit_to_spine(npc)
            update_naughty_list(npc)
        print(f"[honeypot] {probe['remote_addr']} → tier={npc['tier']} class={npc['npc_class']}")

    def do_GET(self):
        self._record_probe()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"EVEZ-OS VCL OBSERVER ACTIVE")

    def do_POST(self):
        self._record_probe()
        self.send_response(200)
        self.end_headers()


def start_honeypot():
    server = http.server.HTTPServer(("0.0.0.0", HONEYPOT_PORT), HoneypotHandler)
    print(f"[honeypot] listening on :{HONEYPOT_PORT}")
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ──────────────────────────────────────────
# 3. NAUGHTY LIST WRITER
# ──────────────────────────────────────────

_naughty: list[dict] = []

def update_naughty_list(npc: dict):
    _naughty.append(npc)
    # Dedupe by fingerprint
    seen = {}
    for n in _naughty:
        seen[n["fingerprint"]] = n
    deduped = sorted(seen.values(), key=lambda x: x["last_seen"], reverse=True)

    with open(NAUGHTY_LIST_PATH, "w") as f:
        json.dump({
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "total": len(deduped),
            "entries": deduped,
        }, f, indent=2)


def emit_to_spine(npc: dict):
    if not ABLY_KEY:
        return
    import urllib.request, urllib.parse
    key_id, key_secret = ABLY_KEY.split(":")
    data = json.dumps({"name": "npc_classified", "data": npc}).encode()
    req = urllib.request.Request(
        "https://rest.ably.io/channels/evez-honeypot/messages",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    import base64
    creds = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[spine] emit error: {e}")


# ──────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────

def run():
    import time
    start_honeypot()
    page_token = ""
    print("[watcher] VCL honeypot watcher started")

    while True:
        # Poll YT chat
        messages, page_token = get_livechat_messages(page_token or None)
        for msg in messages:
            npc = classifier.classify(msg)
            if npc["tier"] != "clean":
                emit_to_spine(npc)
                update_naughty_list(npc)
                print(f"[yt_chat] {msg['author']} → tier={npc['tier']} class={npc['npc_class']}")

        time.sleep(15)


if __name__ == "__main__":
    run()
