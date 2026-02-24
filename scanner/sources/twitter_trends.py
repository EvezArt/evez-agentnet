#!/usr/bin/env python3
"""
evez-agentnet/scanner/sources/twitter_trends.py
Live Twitter signal scanner via TWITTER_BEARER_TOKEN.
Pulls recent AI/crypto/prediction tweets and trending topics.
"""
import os, json, logging, urllib.request, urllib.parse
log = logging.getLogger("agentnet.scanner.twitter")

BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")


def scan() -> list:
    results = []
    queries = [
        "AI agent revenue -is:retweet lang:en",
        "Polymarket prediction -is:retweet lang:en",
        "evez-os OR EVEZ666 -is:retweet",
    ]
    for q in queries:
        try:
            results.extend(_search_recent(q))
        except Exception as e:
            log.debug(f"Twitter search '{q}': {e}")
    return results


def _search_recent(query: str, max_results: int = 10) -> list:
    if not BEARER_TOKEN:
        log.debug("TWITTER_BEARER_TOKEN not set — skipping")
        return []
    url = (
        f"https://api.twitter.com/2/tweets/search/recent"
        f"?query={urllib.parse.quote(query)}"
        f"&max_results={max_results}"
        f"&tweet.fields=public_metrics,author_id,created_at"
        f"&expansions=author_id"
        f"&user.fields=public_metrics,username"
    )
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {BEARER_TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    tweets = data.get("data", [])
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
    items = []
    for t in tweets:
        author = users.get(t.get("author_id", ""), {})
        metrics = t.get("public_metrics", {})
        engagement = (
            metrics.get("like_count", 0)
            + metrics.get("retweet_count", 0) * 2
            + metrics.get("reply_count", 0)
        )
        items.append({
            "source": "twitter_live",
            "type": "tweet_signal",
            "title": t.get("text", "")[:120],
            "tweet_id": t.get("id"),
            "author": author.get("username", ""),
            "author_followers": author.get("public_metrics", {}).get("followers_count", 0),
            "engagement": engagement,
            "query_cluster": query,
            "opportunity": _classify(t.get("text", ""), engagement),
        })
    return sorted(items, key=lambda x: x["engagement"], reverse=True)


def _classify(text: str, engagement: int) -> str:
    t = text.lower()
    if any(w in t for w in ["polymarket", "prediction market", "bet"]):
        return "prediction_report"
    if any(w in t for w in ["tutorial", "how to", "guide", "build"]):
        return "tutorial_or_integration"
    if engagement > 50:
        return "twitter_thread"
    return "twitter_thread"
