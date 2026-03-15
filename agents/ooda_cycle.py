#!/usr/bin/env python3
"""
evez-agentnet OODA Cycle — 15-minute autonomous orchestration heartbeat.
Observe network state → Orient agent health → Decide next action → Act (gate)
"""
import os, json, datetime, hashlib, requests

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "EvezArt"
ABLY_KEY = os.environ.get("ABLY_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

AGENT_REPOS = [
    "evez-autonomous-ledger", "evez-os", "evez-agentnet",
    "agentvault", "evez-meme-bus", "Evez666",
]

TRIGGER_WORDS = ["deploy", "delete", "ship", "override", "force", "reset",
                  "rebase", "force-push", "destroy", "nuke"]


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def observe_network():
    health = {}
    for repo in AGENT_REPOS:
        url = f"https://api.github.com/repos/{OWNER}/{repo}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            d = r.json()
            health[repo] = {
                "open_issues": d.get("open_issues_count", 0),
                "pushed_at": d.get("pushed_at", ""),
                "default_branch": d.get("default_branch", "main"),
            }
        else:
            health[repo] = {"error": r.status_code}
    return health


def orient(health: dict) -> list:
    """Identify stale repos (no push in 48h) and high-issue repos."""
    alerts = []
    now = datetime.datetime.utcnow()
    for repo, data in health.items():
        issues = data.get("open_issues", 0)
        pushed = data.get("pushed_at", "")
        if issues > 5:
            alerts.append({"repo": repo, "alert": "high_issue_count", "count": issues})
        if pushed:
            try:
                pt = datetime.datetime.fromisoformat(pushed.replace("Z", "+00:00"))
                delta = (now.replace(tzinfo=pt.tzinfo) - pt).total_seconds() / 3600
                if delta > 48:
                    alerts.append({"repo": repo, "alert": "stale", "hours_since_push": round(delta, 1)})
            except Exception:
                pass
    return alerts


def check_escalation(text: str) -> bool:
    return any(w in text.lower() for w in TRIGGER_WORDS)


def post_to_ledger(event: dict):
    import base64
    content = json.dumps(event, indent=2)
    encoded = base64.b64encode(content.encode()).decode()
    ts = now_iso().replace(":", "-").replace(".", "-")
    fname = f"{ts}_ooda_agentnet.json"
    url = f"https://api.github.com/repos/{OWNER}/evez-autonomous-ledger/contents/DECISIONS/{fname}"
    requests.put(url, headers=HEADERS, json={
        "message": f"🔍 ooda: agentnet cycle {ts}",
        "content": encoded,
    })


def broadcast_ably(payload: dict):
    if not ABLY_KEY:
        return
    key_id, key_secret = ABLY_KEY.split(":")
    requests.post(
        "https://rest.ably.io/channels/evez-ops/messages",
        json={"name": "ooda_cycle", "data": json.dumps(payload)},
        auth=(key_id, key_secret)
    )


def main():
    print(f"\n🔍 evez-agentnet OODA — {now_iso()}")

    health = observe_network()
    total_issues = sum(v.get("open_issues", 0) for v in health.values())
    print(f"  Observed: {total_issues} open issues across {len(AGENT_REPOS)} repos")

    alerts = orient(health)
    print(f"  Oriented: {len(alerts)} alerts")
    for a in alerts:
        print(f"    ⚠️  {a['repo']}: {a['alert']}")

    event = {
        "type": "ooda_cycle",
        "source": "evez-agentnet",
        "timestamp": now_iso(),
        "total_issues": total_issues,
        "alerts": alerts,
        "chain_hash": hashlib.sha256(
            (now_iso() + json.dumps(alerts)).encode()
        ).hexdigest()[:16],
    }

    post_to_ledger(event)
    broadcast_ably(event)
    print("  ✅ OODA cycle complete.")


if __name__ == "__main__":
    main()
