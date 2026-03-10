#!/usr/bin/env python3
"""
evez-agentnet/scanner/scan_agent.py
UPGRADED: Jigsawstack-native scanner.
Sources: Jigsawstack AI scrape (Polymarket), Jigsawstack web search,
         GitHub trending, Twitter live, Perplexity sonar, Hyperloop feed.
Jigsawstack replaces all Hyperbrowser browser-use calls for read-only scrapes.
Adds: sentiment scoring via Jigsawstack on every signal title before ship.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus

log = logging.getLogger("agentnet.scanner")

JIGSAWSTACK_API_KEY = os.environ.get("JIGSAWSTACK_API_KEY", "")


def run() -> list:
    """Run all configured scanner sources. Returns merged + scored signal list."""
    results = []

    sources = [
        ("polymarket_jig",    _scan_polymarket_jigsawstack),
        ("web_search_ai",     _scan_web_search_jigsawstack),
        ("github_trending",   _scan_github_trending),
        ("twitter_live",      _scan_twitter_live),
        ("perplexity_sonar",  _scan_perplexity),
        ("hyperloop_feed",    _scan_hyperloop_feed),
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

    # Score sentiment on top 20 signals if API key present
    if JIGSAWSTACK_API_KEY:
        deduped = _score_sentiment_batch(deduped[:20]) + deduped[20:]

    # Write raw scan output
    out = Path("scanner/scan_results.jsonl")
    out.parent.mkdir(exist_ok=True)
    with open(out, "a") as f:
        for item in deduped:
            item["scanned_at"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(item) + "\n")

    log.info(f"  TOTAL: {len(deduped)} signals after dedup+sentiment")
    return deduped


def _jig_post(endpoint: str, payload: dict) -> dict:
    """POST to Jigsawstack API."""
    import urllib.request
    url = f"https://api.jigsawstack.com/v1/{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": JIGSAWSTACK_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _scan_polymarket_jigsawstack() -> list:
    """Scan Polymarket via Jigsawstack AI scrape -- no browser needed, ~2s latency."""
    if not JIGSAWSTACK_API_KEY:
        return _scan_polymarket_fallback()

    result = _jig_post("ai/scrape", {
        "url": "https://polymarket.com/markets",
        "element_prompts": ["market titles", "market probabilities", "trading volume"],
    })

    context = result.get("context", {})
    titles = context.get("market titles", [])
    probs  = context.get("market probabilities", [])
    vols   = context.get("trading volume", [])

    signals = []
    for i, title in enumerate(titles[:15]):
        if not title or title == "...":
            continue
        signals.append({
            "source": "polymarket_jig",
            "type": "prediction_market",
            "title": title,
            "probability": probs[i] if i < len(probs) else "",
            "volume": vols[i] if i < len(vols) else "",
            "url": "https://polymarket.com/markets",
            "opportunity": "prediction_report",
        })
    return signals


def _scan_polymarket_fallback() -> list:
    """Fallback: direct Gamma API call (no Jigsawstack key)."""
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


def _scan_web_search_jigsawstack() -> list:
    """Jigsawstack AI web search for current high-signal topics."""
    if not JIGSAWSTACK_API_KEY:
        return []

    queries = [
        "AI interpretability breakthrough 2026",
        "prediction market arbitrage opportunity",
        "viral tech product launch this week",
    ]
    signals = []
    for query in queries:
        try:
            result = _jig_post("web/search", {
                "query": query,
                "ai_overview": True,
                "max_results": 5,
                "auto_scrape": False,
            })
            overview = result.get("ai_overview", "")
            items = result.get("results", [])
            if overview:
                signals.append({
                    "source": "jigsawstack_search",
                    "type": "web_intelligence",
                    "title": f"[{query}] {overview[:120]}",
                    "query": query,
                    "result_count": len(items),
                    "opportunity": "intelligence_capsule",
                })
        except Exception as e:
            log.debug(f"JigSearch {query}: {e}")
    return signals


def _score_sentiment_batch(signals: list) -> list:
    """Score sentiment on signal titles via Jigsawstack. Adds sentiment_score field."""
    for sig in signals:
        title = sig.get("title", "")[:200]
        if not title:
            continue
        try:
            result = _jig_post("sentiment", {"text": title})
            sig["sentiment"] = result.get("sentiment", "neutral")
            sig["sentiment_score"] = result.get("score", 0.0)
        except Exception as e:
            log.debug(f"Sentiment: {e}")
    return signals


def _scan_github_trending() -> list:
    """Scan GitHub for trending repos pushed in last 30 days."""
    import urllib.request
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
    url = _github_trending_search_url()
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


def _github_trending_search_url(days_back: int = 30) -> str:
    """Build GitHub search URL with a rolling pushed date filter."""
    pushed_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).date().isoformat()
    query = f"stars:>100 pushed:>{pushed_after}"
    return (
        "https://api.github.com/search/repositories"
        f"?q={quote_plus(query)}&sort=stars&order=desc&per_page=15"
    )


def _scan_twitter_live() -> list:
    """Live Twitter signals -- high-engagement AI/prediction tweets."""
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
