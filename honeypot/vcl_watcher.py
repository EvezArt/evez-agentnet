#!/usr/bin/env python3
"""
honeypot/vcl_watcher.py — EVEZ-OS VCL Honeypot Watcher (enhanced)

Wires the 24/7 @lordevez VCL YouTube livestream to EVEZ-OS intruder audits
at network honeypot level. Classifies stream actors + network probes into
the 7-class NPC witness taxonomy and emits to:
  - output/naughty_list.json  (public endpoint source)
  - Ably channel: evez-vcl-npc   (livestream reads this for overlay)
  - Ably channel: evez-honeypot  (spine bus)

Pipeline:
  YT Live Chat → auto-discover liveChatId from active @lordevez stream
  Network Probes → low-interaction honeypot on HONEYPOT_PORT
  → NPCClassifier.classify()
  → naughty_list.json + Ably emit

Self-automating: re-discovers live chat ID if stream resets.
"""

import os, sys, json, time, socket, threading, http.server
import hashlib, datetime, base64
import urllib.request, urllib.parse
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
from npc_classifier import NPCClassifier

ABLY_KEY       = os.environ.get("ABLY_API_KEY", "")
YT_API_KEY     = os.environ.get("YT_API_KEY", "")
LIVECHAT_ID    = os.environ.get("YT_LIVECHAT_ID", "")   # auto-discovered if blank
YT_CHANNEL_ID  = os.environ.get("YT_CHANNEL_ID", "UClordevez")   # @lordevez channel
HONEYPOT_PORT  = int(os.environ.get("HONEYPOT_PORT", "18666"))
OUTPUT_PATH    = "output/naughty_list.json"
SPINE_CHANNEL  = "evez-honeypot"
STREAM_CHANNEL = "evez-vcl-npc"

classifier = NPCClassifier()
_naughty_list: list[dict] = []
_list_lock    = threading.Lock()
_chat_id      = LIVECHAT_ID
_page_token   = ""


# ── ABLY EMIT ─────────────────────────────────────────────────────────────────

def ably_publish(channel: str, data: dict):
    if not ABLY_KEY:
        return
    try:
        key_id, key_secret = ABLY_KEY.split(":", 1)
        token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
        url = f"https://rest.ably.io/channels/{urllib.parse.quote(channel)}/messages"
        payload = json.dumps({"name": "npc_event", "data": data}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Authorization": f"Basic {token}",
                     "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=8) as r:
            pass
    except Exception as e:
        print(f"[ably] publish error: {e}", flush=True)


# ── WRITE NAUGHTY LIST ────────────────────────────────────────────────────────

def persist_record(record: dict):
    with _list_lock:
        _naughty_list.append(record)
        # keep only last 500
        trimmed = _naughty_list[-500:]
        _naughty_list.clear()
        _naughty_list.extend(trimmed)
        os.makedirs("output", exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            json.dump(_naughty_list, f, indent=2, default=str)
    # emit to both Ably channels
    ably_publish(SPINE_CHANNEL,  record)
    ably_publish(STREAM_CHANNEL, record)


# ── YOUTUBE LIVE CHAT ID DISCOVERY ───────────────────────────────────────────

def discover_live_chat_id() -> str:
    """Auto-discover liveChatId from active stream on the channel."""
    global _chat_id
    if _chat_id:
        return _chat_id
    if not YT_API_KEY:
        print("[watcher] no YT_API_KEY — can't discover liveChatId", flush=True)
        return ""
    try:
        # search for active live broadcasts on the EVEZ channel
        url = (f"https://www.googleapis.com/youtube/v3/search"
               f"?part=id&channelId={YT_CHANNEL_ID}&type=video"
               f"&eventType=live&key={YT_API_KEY}")
        req = urllib.request.Request(url, headers={"User-Agent": "evez-os/2.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        items = data.get("items", [])
        if not items:
            print("[watcher] no active live stream found on channel", flush=True)
            return ""
        video_id = items[0]["id"]["videoId"]
        # get liveStreamingDetails for this video
        url2 = (f"https://www.googleapis.com/youtube/v3/videos"
                f"?part=liveStreamingDetails&id={video_id}&key={YT_API_KEY}")
        req2 = urllib.request.Request(url2, headers={"User-Agent": "evez-os/2.0"})
        with urllib.request.urlopen(req2, timeout=10) as r2:
            data2 = json.loads(r2.read())
        details = data2["items"][0]["liveStreamingDetails"]
        lcid = details.get("activeLiveChatId", "")
        if lcid:
            _chat_id = lcid
            print(f"[watcher] discovered liveChatId: {lcid}", flush=True)
        return lcid
    except Exception as e:
        print(f"[watcher] discovery error: {e}", flush=True)
        return ""


# ── YOUTUBE CHAT COLLECTOR ────────────────────────────────────────────────────

def get_livechat_messages(page_token: str = "") -> tuple[list[dict], str]:
    lcid = _chat_id or discover_live_chat_id()
    if not lcid or not YT_API_KEY:
        return [], ""
    try:
        url = (f"https://www.googleapis.com/youtube/v3/liveChat/messages"
               f"?liveChatId={lcid}&part=snippet,authorDetails&key={YT_API_KEY}"
               f"{'&pageToken=' + page_token if page_token else ''}")
        req = urllib.request.Request(url, headers={"User-Agent": "evez-os/2.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        messages = [
            {
                "source":            "yt_chat",
                "author":            item["authorDetails"]["displayName"],
                "author_id":         item["authorDetails"]["channelId"],
                "is_verified":       item["authorDetails"]["isVerified"],
                "is_chat_moderator": item["authorDetails"]["isChatModerator"],
                "is_chat_sponsor":   item["authorDetails"]["isChatSponsor"],
                "channel_url":       item["authorDetails"].get("channelUrl", ""),
                "text":              item["snippet"]["displayMessage"],
                "published_at":      item["snippet"]["publishedAt"],
            }
            for item in data.get("items", [])
        ]
        return messages, data.get("nextPageToken", "")
    except Exception as e:
        print(f"[watcher] YT chat error: {e}", flush=True)
        # if chat ID went stale, force rediscovery next cycle
        if "liveChatNotFound" in str(e) or "403" in str(e):
            global _chat_id
            _chat_id = ""
        return [], ""


# ── NETWORK HONEYPOT ──────────────────────────────────────────────────────────

class HoneypotHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _record_probe(self):
        probe = {
            "source":     "network_probe",
            "remote_addr": self.client_address[0],
            "method":     self.command,
            "path":       self.path,
            "user_agent": self.headers.get("User-Agent", ""),
            "host":       self.headers.get("Host", ""),
            "referer":    self.headers.get("Referer", ""),
            "timestamp":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        result = classifier.classify(probe)
        result["source_type"] = "network_probe"
        print(f"[honeypot] {probe['remote_addr']} → {result['npc_class']} ({result['tier']})", flush=True)
        persist_record(result)

    def do_GET(self):
        self._record_probe()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_POST(self): self.do_GET()
    def do_HEAD(self): self.do_GET()


def run_honeypot():
    try:
        server = http.server.HTTPServer(("0.0.0.0", HONEYPOT_PORT), HoneypotHandler)
        print(f"[honeypot] listening on :{HONEYPOT_PORT}", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[honeypot] failed to bind port {HONEYPOT_PORT}: {e}", flush=True)


# ── MAIN WATCH LOOP ────────────────────────────────────────────────────────────

def chat_loop():
    global _page_token
    print("[watcher] chat loop starting...", flush=True)
    seen_authors: set = set()

    while True:
        msgs, next_token = get_livechat_messages(_page_token)
        if next_token:
            _page_token = next_token

        for msg in msgs:
            # classify each chat message
            result = classifier.classify(msg)
            result["source_type"] = "yt_chat"

            # first-time author: enhanced OSINT note
            if msg["author_id"] not in seen_authors:
                result["first_seen"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                seen_authors.add(msg["author_id"])

            if result["npc_class"] != "UNCLASSIFIED" or result["tier"] != "clean":
                print(f"[watcher] {msg['author'][:20]} → {result['npc_class']} tier={result['tier']}", flush=True)
                persist_record(result)

        time.sleep(15)


def main():
    print("[watcher] EVEZ VCL Honeypot Watcher starting", flush=True)
    print(f"[watcher] YT_API_KEY: {'set' if YT_API_KEY else 'missing'}", flush=True)
    print(f"[watcher] ABLY_KEY: {'set' if ABLY_KEY else 'missing'}", flush=True)
    print(f"[watcher] LIVECHAT_ID: {_chat_id or 'auto-discover'}", flush=True)

    # start honeypot in background
    threading.Thread(target=run_honeypot, daemon=True).start()

    # start chat loop
    discover_live_chat_id()
    chat_loop()


if __name__ == "__main__":
    main()
