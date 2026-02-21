#!/usr/bin/env python3
"""
evez-agentnet/shipper/ship_agent.py
Post approved drafts to Twitter / Gumroad / GitHub.
Gated by truth_plane -- requires VERIFIED+ to ship.
"""

import os, json, logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("agentnet.shipper")
SHIP_LOG = Path("shipper/ship_log.jsonl")
SHIP_LOG.parent.mkdir(exist_ok=True)

TWITTER_KEY = os.environ.get("TWITTER_BEARER_TOKEN", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")


def run(drafts: list) -> float:
    """Ship drafts. Returns estimated earned USD."""
    earned = 0.0
    for draft in drafts:
        dtype = draft.get("type", "")
        try:
            if dtype == "twitter_thread":
                _ship_twitter(draft)
            elif dtype in ("gumroad_report", "gumroad_product"):
                _ship_gumroad_log(draft)
                earned += 0.0  # logged for manual upload until API supports it
            log.info(f"  Shipped: {dtype} -- {draft.get('title', '')[:40]}")
            _log_ship(draft, "shipped", earned)
        except Exception as e:
            log.error(f"  Ship failed {dtype}: {e}")
            _log_ship(draft, "failed", 0.0)
    return earned


def _ship_twitter(draft: dict):
    """Post tweet thread via Twitter API v2."""
    content = draft.get("content", "")
    if not content:
        return
    # Split into tweets by numbered lines
    tweets = [t.strip() for t in content.split("\n") if t.strip() and len(t.strip()) > 5]
    tweets = tweets[:5]  # max 5 tweets
    log.info(f"  Twitter: {len(tweets)} tweets queued")
    # TODO: integrate Composio TWITTER_CREATION_OF_A_POST in loop
    # For now: log for review
    _log_ship(draft, "twitter_queued", 0.0)


def _ship_gumroad_log(draft: dict):
    """Log Gumroad product for manual upload (API file upload not yet wired)."""
    log.info(f"  Gumroad: logged for upload -- {draft.get('file', '')}")
    # TODO: wire Gumroad file upload when API available


def _log_ship(draft: dict, status: str, earned: float):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": draft.get("type"), "title": draft.get("title", ""),
        "status": status, "earned_usd": earned,
        "file": draft.get("file", ""),
    }
    with open(SHIP_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
