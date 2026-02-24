#!/usr/bin/env python3
"""
evez-agentnet/scanner/sources/perplexity_signals.py
Live intelligence signals via Perplexity AI sonar-pro.
Queries trending AI/crypto/agent topics for opportunity synthesis.
"""
import os, json, logging, urllib.request
log = logging.getLogger("agentnet.scanner.perplexity")

PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY", "")

SIGNAL_QUERIES = [
    "what AI agent frameworks are trending this week with revenue potential",
    "top Polymarket markets by volume today with analysis opportunity",
    "new AI tools and APIs released in the last 48 hours worth covering",
    "autonomous AI agent income strategies trending in tech twitter",
]


def scan() -> list:
    if not PERPLEXITY_KEY:
        log.debug("PERPLEXITY_API_KEY not set — skipping")
        return []
    results = []
    for query in SIGNAL_QUERIES[:2]:  # 2 queries per run, budget-aware
        try:
            signals = _query_sonar(query)
            results.extend(signals)
        except Exception as e:
            log.debug(f"Perplexity '{query}': {e}")
    return results


def _query_sonar(query: str) -> list:
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": (
                "You are a market intelligence scanner for EVEZ-OS agentnet. "
                "Return a JSON array of 3-5 signals. Each signal: "
                '{"title": str, "summary": str, "opportunity": str, "url": str}. '
                "opportunity must be one of: prediction_report, twitter_thread, "
                "tutorial_or_integration, gumroad_product. Raw JSON only, no markdown."
            )},
            {"role": "user", "content": query},
        ],
        "max_tokens": 400,
        "temperature": 0.2,
        "return_citations": True,
    }
    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {PERPLEXITY_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read())
    content = resp["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    signals = json.loads(content)
    citations = resp.get("citations", [])
    return [{
        "source": "perplexity_sonar",
        "type": "intelligence_signal",
        "title": s.get("title", ""),
        "summary": s.get("summary", ""),
        "opportunity": s.get("opportunity", "twitter_thread"),
        "url": s.get("url") or (citations[i] if i < len(citations) else ""),
        "query_cluster": query,
    } for i, s in enumerate(signals)]
