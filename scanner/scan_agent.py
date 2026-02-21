#!/usr/bin/env python3
"""
evez-agentnet/scanner/scan_agent.py
Pulls live signals from configured sources.
Sources: Polymarket, GitHub trending, jobs boards, Twitter trends.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.scanner")


def run() -> list:
    """Run all configured scanner sources. Returns ranked signal list."""
    results = []

    sources = [
        _scan_polymarket,
        _scan_github_trending,
        _scan_groq_jobs,
        _scan_twitter_trends,
    ]

    for source_fn in sources:
        try:
            items = source_fn()
            results.extend(items)
            log.info(f"  {source_fn.__name__}: {len(items)} signals")
        except Exception as e:
            log.warning(f"  {source_fn.__name__} failed: {e}")

    # Write raw scan output
    out = Path("scanner/scan_results.jsonl")
    out.parent.mkdir(exist_ok=True)
    with open(out, "a") as f:
        for item in results:
            item["scanned_at"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(item) + "\n")

    return results


def _scan_polymarket() -> list:
    """Scan Polymarket for high-volume prediction markets (opportunity: prediction reports)."""
    import urllib.request
    try:
        url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=20&order=volume&ascending=false"
        req = urllib.request.Request(url, headers={"User-Agent": "evez-agentnet/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        return [{
            "source": "polymarket",
            "type": "prediction_market",
            "title": m.get("question", ""),
            "volume_usd": float(m.get("volume", 0)),
            "end_date": m.get("endDate", ""),
            "url": f"https://polymarket.com/event/{m.get('slug', '')}",
            "opportunity": "prediction_report",
        } for m in (data if isinstance(data, list) else data.get("markets", []))]
    except Exception as e:
        log.debug(f"Polymarket: {e}")
        return []


def _scan_github_trending() -> list:
    """Scan GitHub trending for hot repos (opportunity: integration, tutorial, tooling)."""
    import urllib.request
    try:
        url = "https://api.github.com/search/repositories?q=stars:>100+pushed:>2026-02-01&sort=stars&order=desc&per_page=10"
        req = urllib.request.Request(url, headers={
            "User-Agent": "evez-agentnet/1.0",
            "Accept": "application/vnd.github.v3+json"
        })
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
    except Exception as e:
        log.debug(f"GitHub trending: {e}")
        return []


def _scan_groq_jobs() -> list:
    """Placeholder: scan job boards for AI/ML roles (opportunity: resume/cover letter gen)."""
    # TODO: integrate Adzuna/Indeed/RemoteOK API
    return [{
        "source": "jobs_placeholder",
        "type": "job_opportunity",
        "title": "AI Engineer - multiple openings",
        "opportunity": "resume_cover_letter_gen",
        "volume": "high",
    }]


def _scan_twitter_trends() -> list:
    """Placeholder: scan Twitter trending topics (opportunity: timely thread generation)."""
    # TODO: integrate Twitter trends API
    return [{
        "source": "twitter_trends_placeholder",
        "type": "trend",
        "title": "AI agent frameworks trending",
        "opportunity": "twitter_thread",
        "volume": "high",
    }]
