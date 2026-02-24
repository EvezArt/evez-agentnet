#!/usr/bin/env python3
"""
evez-agentnet/scanner/scan_agent.py
Pulls live signals from all configured sources.
Sources: Polymarket, GitHub trending, Twitter live, Perplexity sonar, Hyperloop feed.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.scanner")


def run() -> list:
    """Run all configured scanner sources. Returns merged signal list."""
    results = []

    sources = [
        ("polymarket",         _scan_polymarket),
        ("github_trending",    _scan_github_trending),
        ("twitter_live",       _scan_twitter_live),
        ("perplexity_sonar",   _scan_perplexity),
        ("hyperloop_feed",     _scan_hyperloop_feed),
    ]

    for name, fn in sources:
        try:
            items = fn()
            results.extend(items)
            log.info(f"  {name}: {len(items)} signals")
        except Exception as e:
            log.warning(f"  {name} failed: {e}")

    # Deduplicate by title
    seen = set()
    deduped = []
    for item in results:
        key = item.get("title", "")[:80]
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # Write raw scan output
    out = Path("scanner/scan_results.jsonl")
    out.parent.mkdir(exist_ok=True)
    with open(out, "a") as f:
        for item in deduped:
            item["scanned_at"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(item) + "\n")

    log.info(f"  TOTAL: {len(deduped)} signals after dedup")
    return deduped


def _scan_polymarket() -> list:
    """Scan Polymarket for high-volume prediction markets."""
    import urllib.request
    url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=20&order=volume&ascending=false"
    req = urllib.request.Request(url, headers={"User-Agent": "evez-agentnet/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    markets = data if isinstance(data, list) else data.get("markets", [])
    return [{
        "source": "polymarket",
        "type": "prediction_market",
        "title": m.get("question", ""),
        "volume_usd": float(m.get("volume", 0)),
        "end_date": m.get("endDate", ""),
        "url": f"https://polymarket.com/event/{m.get('slug', '')}",
        "opportunity": "prediction_report",
    } for m in markets]


def _scan_github_trending() -> list:
    """Scan GitHub for trending repos pushed in last 30 days."""
    import urllib.request
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
    url = "https://api.github.com/search/repositories?q=stars:>100+pushed:>2026-01-25&sort=stars&order=desc&per_page=15"
    headers = {"User-Agent": "evez-agentnet/1.0", "Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    return [{
        "source": "github_trending",
        "type": "trending_repo",
        "title": repo.get("full_name", ""),
        "description": repo.get("description", ""),
        "stars": repo.get("stargazers_count", 0),
        "language": repo.get("language", ""),
        "url": repo.get("html_url", ""),
        "opportunity": "tutorial_or_integration",
    } for repo in data.get("items", [])]


def _scan_twitter_live() -> list:
    """Live Twitter signals — high-engagement AI/prediction tweets."""
    try:
        from scanner.sources.twitter_trends import scan
        return scan()
    except Exception as e:
        log.debug(f"Twitter live: {e}")
        return []


def _scan_perplexity() -> list:
    """Intelligence signals from Perplexity sonar-pro."""
    try:
        from scanner.sources.perplexity_signals import scan
        return scan()
    except Exception as e:
        log.debug(f"Perplexity sonar: {e}")
        return []


def _scan_hyperloop_feed() -> list:
    """Live signals from EVEZ-OS hyperloop state (watchlist, probes, milestones)."""
    try:
        from scanner.sources.hyperloop_feed import scan
        return scan()
    except Exception as e:
        log.debug(f"Hyperloop feed: {e}")
        return []
