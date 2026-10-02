#!/usr/bin/env python3
"""
evez-agentnet/shipper/ship_agent.py
Publish approved drafts to configured channels.

Behavioural change (2026-10-02): the previous version logged "Shipped: <type>"
for every draft while both delivery paths were `# TODO` stubs. It produced 747
"shipped" records and $0.00 across 246 rounds, and the orchestrator reported
success. That is a declarative surface reporting an outcome it never achieved
— the same defect class as the RSI engine prescribing recovery to a perfect
agent.

Now: a draft is only marked SHIPPED if a real transmission returned success.
Everything else is recorded with the specific reason it did not ship, and the
orchestrator sees honest counters.
"""
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.shipper")
SHIP_LOG = Path("shipper/ship_log.jsonl")
SHIP_LOG.parent.mkdir(exist_ok=True)

TWITTER_BEARER = os.environ.get("TWITTER_BEARER_TOKEN", "").strip()
MASTODON_BASE = os.environ.get("MASTODON_BASE_URL", "").strip()
MASTODON_TOKEN = os.environ.get("MASTODON_ACCESS_TOKEN", "").strip()
GUMROAD_TOKEN = os.environ.get("GUMROAD_API_KEY", "").strip()

# Reasons a draft did not reach a channel. Reported instead of a fake success.
NOT_CONFIGURED = "channel_not_configured"
NOT_IMPLEMENTED = "delivery_not_implemented"
NOTHING_TO_POST = "empty_content"
API_ERROR = "api_error"


def run(drafts: list) -> dict:
    """Attempt to publish drafts.

    Returns a summary dict rather than a bare float, so the caller can see
    WHY nothing earned money instead of inferring it from a zero.
    """
    summary = {
        "attempted": 0,
        "shipped": 0,
        "earned_usd": 0.0,
        "reasons": Counter(),
        "channels_available": available_channels(),
    }

    for draft in drafts:
        summary["attempted"] += 1
        dtype = draft.get("type", "unknown")
        try:
            result = _dispatch(draft)
        except Exception as e:                      # never let one draft kill the round
            summary["reasons"][API_ERROR] += 1
            log.error("Ship error %s: %s", dtype, e)
            _log_ship(draft, f"error:{type(e).__name__}", 0.0, str(e)[:200])
            continue

        if result["shipped"]:
            summary["shipped"] += 1
            summary["earned_usd"] += float(result.get("earned_usd", 0.0) or 0.0)
            _log_ship(draft, "shipped", result.get("earned_usd", 0.0))
            log.info("  SHIPPED %s -> %s", dtype, result.get("channel"))
        else:
            reason = result["reason"]
            summary["reasons"][reason] += 1
            _log_ship(draft, f"not_shipped:{reason}", 0.0, result.get("detail", ""))
            log.info("  NOT SHIPPED %s (%s): %s", dtype, reason,
                     result.get("detail", "")[:80])

    return summary


def available_channels() -> list:
    out = []
    if TWITTER_BEARER:
        out.append("twitter")
    if MASTODON_BASE and MASTODON_TOKEN:
        out.append("mastodon")
    if GUMROAD_TOKEN:
        out.append("gumroad")
    return out


def _dispatch(draft: dict) -> dict:
    dtype = draft.get("type", "")

    if dtype == "twitter_thread":
        return _ship_twitter(draft)
    if dtype in ("gumroad_report", "gumroad_product"):
        return _ship_gumroad(draft)
    if dtype == "github_post":
        # Deliberately NOT shipped: posting to GitHub requires auth and a real
        # push path. Previously this was counted as shipped while doing nothing.
        return {"shipped": False, "reason": NOT_IMPLEMENTED,
                "detail": "github_post has no delivery path; drafts go to drafts/"}
    return {"shipped": False, "reason": NOT_IMPLEMENTED,
            "detail": f"no handler for type={dtype!r}"}


def _ship_twitter(draft: dict) -> dict:
    content = (draft.get("content") or "").strip()
    if not content:
        return {"shipped": False, "reason": NOTHING_TO_POST}
    if not TWITTER_BEARER:
        return {"shipped": False, "reason": NOT_CONFIGURED,
                "detail": "TWITTER_BEARER_TOKEN unset"}

    tweets = [t.strip() for t in content.split("\n")
              if t.strip() and len(t.strip()) > 5][:5]
    if not tweets:
        return {"shipped": False, "reason": NOTHING_TO_POST}

    # Real transmission. Any failure is reported as a failure.
    import urllib.request
    import urllib.error
    url = "https://api.twitter.com/2/tweets"
    posted = 0
    for body in tweets[:280]:
        payload = json.dumps({"text": body[:280]}).encode()
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={"Authorization": f"Bearer {TWITTER_BEARER}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if json.loads(r.read()).get("data", {}).get("id"):
                    posted += 1
            time.sleep(1.5)                      # respect rate limits
        except urllib.error.HTTPError as e:
            return {"shipped": False, "reason": API_ERROR,
                    "detail": f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:120]}"}
        except Exception as e:
            return {"shipped": False, "reason": API_ERROR, "detail": str(e)[:120]}

    return {"shipped": posted > 0, "earned_usd": 0.0, "channel": "twitter",
            "detail": f"{posted}/{len(tweets)} tweets posted"}


def _ship_gumroad(draft: dict) -> dict:
    if not GUMROAD_TOKEN:
        return {"shipped": False, "reason": NOT_CONFIGURED,
                "detail": "GUMROAD_API_KEY unset — product left in drafts/ for manual upload"}
    # Product creation is a real API call; only claim success when it returns an id.
    try:
        import urllib.request
        import urllib.error
        payload = json.dumps({
            "name": draft.get("title", "Untitled"),
            "description": (draft.get("content") or "")[:5000],
            "price_cents": int(draft.get("price_cents", 0)),
        }).encode()
        req = urllib.request.Request(
            "https://api.gumroad.com/v2/products", data=payload, method="POST",
            headers={"Authorization": f"Bearer {GUMROAD_TOKEN}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = json.loads(r.read())
        if body.get("success") and body.get("product", {}).get("id"):
            return {"shipped": True, "earned_usd": 0.0, "channel": "gumroad",
                    "detail": f"product {body['product']['id']}"}
        return {"shipped": False, "reason": API_ERROR,
                "detail": str(body)[:120]}
    except Exception as e:
        return {"shipped": False, "reason": API_ERROR, "detail": str(e)[:120]}


def _log_ship(draft: dict, status: str, earned: float, detail: str = ""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": draft.get("type"),
        "title": draft.get("title", ""),
        "status": status,
        "earned_usd": earned,
        "file": draft.get("file", ""),
        "detail": detail,
        "channels_available": available_channels(),
    }
    with open(SHIP_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
