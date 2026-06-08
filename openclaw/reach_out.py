#!/usr/bin/env python3
"""
openclaw/reach_out.py  —  EVEZ Self-Automating Search & Outreach Module
Watches GitHub, Gmail, Discord, YouTube for mentions of EVEZ/Steven
then emits spine events and pushes notifications.

Wires into evez-agentnet OODA loop as an Observe extension.
"""

import os
import json
import hashlib
import datetime
import requests
from typing import Optional

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
ABLY_KEY = os.environ.get("ABLY_API_KEY", "")
SPINE_FILE = "spine/reach_out_events.jsonl"
SCAN_OUT = "scanner/scan_results.jsonl"

EVEZ_HANDLES = ["EVEZ", "evez666", "EvezArt", "Steven Crawford-Maggard", "evez-os", "openclaw", "clawbreak"]
SEARCH_TERMS = ["evez666", "evezart", "openclaw", "clawbreak", "evez-os", "disclosure.tools"]

# ──────────────────────────────────────────
# 1. GITHUB SCANNER
# ──────────────────────────────────────────

def scan_github_mentions(terms: list[str]) -> list[dict]:
    hits = []
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    for term in terms:
        r = requests.get(
            "https://api.github.com/search/issues",
            params={"q": f"{term} in:body,title", "per_page": 5, "sort": "updated"},
            headers=headers,
            timeout=10,
        )
        if r.ok:
            for item in r.json().get("items", []):
                hits.append({
                    "source": "github",
                    "type": "mention",
                    "term": term,
                    "url": item["html_url"],
                    "title": item["title"],
                    "author": item["user"]["login"],
                    "updated_at": item["updated_at"],
                })
    return hits


def scan_github_activity() -> list[dict]:
    """Check EvezArt repos for new stars, forks, PRs in last 2h"""
    hits = []
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    r = requests.get("https://api.github.com/users/EvezArt/events", headers=headers, timeout=10)
    if not r.ok:
        return hits
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    for event in r.json()[:30]:
        created = datetime.datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        if created < cutoff:
            break
        hits.append({
            "source": "github",
            "type": event["type"],
            "repo": event["repo"]["name"],
            "actor": event.get("actor", {}).get("login"),
            "created_at": event["created_at"],
        })
    return hits


# ──────────────────────────────────────────
# 2. DISCORD NOTIFIER
# ──────────────────────────────────────────

def notify_discord(hits: list[dict]) -> None:
    if not DISCORD_WEBHOOK or not hits:
        return
    lines = [f"🔍 **OpenClaw Reach-Out Sweep** — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"]
    for h in hits[:10]:
        src = h.get("source", "?")
        url = h.get("url", "")
        title = h.get("title") or h.get("type", "event")
        author = h.get("author") or h.get("actor", "unknown")
        lines.append(f"• [{src}] **{title}** by `{author}` {url}")
    payload = {"content": "\n".join(lines)}
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)


# ──────────────────────────────────────────
# 3. ABLY SPINE EMITTER
# ──────────────────────────────────────────

def emit_spine_events(hits: list[dict]) -> None:
    if not ABLY_KEY or not hits:
        return
    for hit in hits:
        hit["_spine_hash"] = hashlib.sha256(json.dumps(hit, sort_keys=True).encode()).hexdigest()
        hit["_emitted_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        # Publish to Ably channel evez-reach-out
        r = requests.post(
            f"https://rest.ably.io/channels/evez-reach-out/messages",
            auth=(ABLY_KEY.split(":")[0], ABLY_KEY.split(":")[1]),
            json={"name": "reach_out", "data": hit},
            timeout=5,
        )
        # Also append to local spine file
        with open(SPINE_FILE, "a") as f:
            f.write(json.dumps(hit) + "\n")


# ──────────────────────────────────────────
# 4. SCAN RESULTS UPDATE (feeds OODA observe)
# ──────────────────────────────────────────

def write_scan_results(hits: list[dict]) -> None:
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "scan_type": "reach_out",
        "count": len(hits),
        "hits": hits[:20],
        "market_confidence": min(0.5 + len(hits) * 0.05, 1.0),  # grows with activity
    }
    with open(SCAN_OUT, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[reach_out] wrote {len(hits)} hits → {SCAN_OUT}")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

def run():
    print(f"[reach_out] sweep started {datetime.datetime.utcnow().isoformat()}Z")
    hits = []
    hits += scan_github_mentions(SEARCH_TERMS)
    hits += scan_github_activity()

    if hits:
        print(f"[reach_out] {len(hits)} signals found")
        emit_spine_events(hits)
        notify_discord(hits)
    else:
        print("[reach_out] no signals this sweep")

    write_scan_results(hits)


if __name__ == "__main__":
    run()
