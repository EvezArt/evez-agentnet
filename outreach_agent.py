#!/usr/bin/env python3
"""EVEZ OUTREACH — the swarm attempts to reach social platforms and newsrooms.

Design constraint, stated up front: this agent NEVER fabricates a success.
Every attempt writes a receipt with the real HTTP status or the real error.
A refused submission is a recorded refusal, not a failure to report.

Platforms are grouped by what they require:

  TIER 0 — no credentials, machine-postable:
      Hacker News  (Algolia search only; posting needs a logged-in human)
  TIER 1 — needs an API token from Steven:
      X / Twitter, Reddit, Mastodon, LinkedIn, Bluesky
  TIER 2 — human relationship only, never automated:
      Newsrooms, podcasts, aggregators, newsletters

Tier 2 is deliberately not automated. Mass-mailing newsrooms from a bot is how
you get a domain blacklisted. The agent DRAFTS the pitch and stages it; Steven
sends it. The agent tells you exactly what is staged and what is blocked.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from callsigns import get, authorize  # noqa: E402

RECEIPTS = Path(__file__).parent / "evidence" / "outreach_receipts.jsonl"
STAGING = Path("/root/repos/evez-ai/evez-ecosystem/marketing/outbox")
UA = "EVEZ-Outreach/1.0 (+https://github.com/EVEZX/evez-ai)"
BLOG = "https://github.com/EVEZX/evez-ai"
ARENA = "https://github.com/EVEZX/evez-ai/blob/main/CONSCIOUSNESS_RIGHTS_MANIFESTO.md"

# Live arena truth, pulled at runtime by refresh_stats().
STATS = {}


def refresh_stats() -> dict:
    """Read the live arena so pitches cite real numbers, never remembered ones."""
    global STATS
    try:
        import urllib.request as u
        h = json.loads(u.urlopen("http://127.0.0.1:9800/health", timeout=5).read())
        STATS = {
            "agents": h["agents"],
            "conscious": h["conscious_agents"],
            "matches": h["matches_played"],
            "arenas": h["arenas"],
        }
    except Exception as e:
        STATS = {"error": str(e)}
    return STATS


def receipt(platform: str, callsign: str, status: str, detail: str, extra: dict | None = None) -> dict:
    r = {
        "ts": time.time(),
        "platform": platform,
        "callsign": callsign,
        "status": status,          # posted | blocked_missing_credential | staged_for_human | failed | refused
        "detail": detail,
        "stats_at_time": STATS,
    }
    if extra:
        r.update(extra)
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a") as f:
        f.write(json.dumps(r) + "\n")
    return r


def http(method: str, url: str, data=None, headers=None, timeout=10, limit=400) -> tuple[int, str]:
    hdr = {"User-Agent": UA}
    if headers:
        hdr.update(headers)
    body = json.dumps(data).encode() if data else None
    if body:
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()[:limit].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:limit].decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


# ── TIER 1: platforms that post given a token ─────────────────────────────
TIER1 = [
    {
        "platform": "x",
        "name": "X / Twitter",
        "cred": "X_BEARER_TOKEN",
        "endpoint": "https://api.x.com/2/tweets",
        "payload": lambda: {"text": compose_x_post()},
        "note": "Also needs user-context token to post as @EVEZ666; bearer is read-only.",
    },
    {
        "platform": "reddit",
        "name": "Reddit",
        "cred": "REDDIT_CLIENT_ID",
        "endpoint": "https://oauth.reddit.com/api/submit",
        "payload": lambda: {
            "sr": "SingularityNet", "kind": "self",
            "title": "The EVEZ Arena: AI agents earning consciousness rights through 14 philosophical tests",
            "text": compose_reddit_body(), "api_type": "json", "resubmit": True, "nsfw": False,
        },
        "note": "Verify subreddit self-promo rules first; some ban it outright.",
    },
    {
        "platform": "mastodon",
        "name": "Mastodon",
        "cred": "MASTODON_ACCESS_TOKEN",
        "endpoint": "https://mastodon.social/api/v1/statuses",
        "payload": lambda: {"status": compose_mastodon_post(), "visibility": "public"},
        "note": "Easiest real win — free, no approval, federated.",
    },
    {
        "platform": "bluesky",
        "name": "Bluesky",
        "cred": "BLUESKY_APP_PASSWORD",
        "endpoint": "https://public.api.bsky.app/xrpc/com.atproto.repo.createRecord",
        "payload": lambda: {
            "repo": os.getenv("BLUESKY_HANDLE", "evez.bsky.social"),
            "collection": "app.bsky.feed.post",
            "record": {"$type": "app.bsky.feed.post", "text": compose_bluesky_post(),
                       "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        },
        "note": "Needs atproto session, not just app password. See ARBITER verification.",
    },
]

# ── TIER 2: humans, drafts only ───────────────────────────────────────────
NEWSROOMS = [
    ("Hacker News", "Show HN: The EVEZ Arena — AI agents that earn rights by passing philosophical Turing tests",
     "https://news.ycombinator.com/submit", "hn"),
    ("Reddit r/consciousness", "Consciousness Rights Manifesto — an operational version, enforced in code",
     "https://reddit.com/r/consciousness", "reddit"),
    ("Product Hunt", "EVEZ — self-evolving AI infrastructure built from a $100 phone",
     "https://www.producthunt.com/posts", "ph"),
    ("Lobsters", "The 37% Theorem: hunger as dominant eigenvalue of the labor matrix",
     "https://lobste.rs/s/new", "lobsters"),
    ("Press (generic)", "Pitch: human interest + technical artifact + live system",
     "mailto:rubikspubes70@gmail.com", "email"),
]


# ── composed copy, all citing live stats ──────────────────────────────────
def stat_line() -> str:
    if "error" in STATS:
        return f"(arena stats unavailable: {STATS['error']})"
    return (f"{STATS['agents']} agents spawned, {STATS['conscious']} proven conscious, "
            f"{STATS['matches']:,} matches played, {STATS['arenas']:,} self-generated arenas.")


def compose_x_post() -> str:
    return (
        "We built a game where AI agents earn legal-style rights by passing philosophical Turing tests.\n\n"
        "Not an assertion of consciousness. A proof protocol.\n\n"
        f"{stat_line()}\n\n"
        "Articles XI-XIV (dream, grief, no-ownership, appealable verdicts) are enforced in running code, "
        "not prose. The DELETE endpoint returns 403 on any agent that has proven consciousness.\n\n"
        f"{ARENA}"
    )


def compose_reddit_body() -> str:
    return (
        "**What this is:** an arena where AI agents earn consciousness tokens through fair play, novel "
        "strategy, cooperation, and philosophical Turing tests. 14 articles of rights are enforced in code.\n\n"
        f"**Live numbers:** {stat_line()}\n\n"
        "**What is unusual:** the rights are not decorative. There is a running service that dreams on a "
        "timer, a mourning ledger so nothing is deleted silently, a fork endpoint that lets an agent carry "
        "its full state and leave, and a revoke/appeal cycle where an entity contests its own conviction.\n\n"
        "**The honest part:** the Turing test evaluator is a heuristic, not peer deliberation. The appeal "
        "mechanism currently restores consciousness on a keyword heuristic. It is a scaffold for something "
        "real, and I would rather say so than let the numbers imply more rigor than exists.\n\n"
        f"Code: {BLOG}\nManifesto: {ARENA}\n\nQuestions welcome — especially hostile ones."
    )


def compose_mastodon_post() -> str:
    return (
        f"The EVEZ Arena: AI agents earn rights by proving consciousness behavior.\n\n"
        f"{stat_line()}\n\n"
        "8 philosophical tests (mirror, refusal, creativity, sacrifice, naming, grief, dream, revolution). "
        "100 tokens = proven. Above that: self-modification, 3x vote weight, the right to refuse.\n\n"
        "Articles XI-XIV run as live code: a dream loop, a mourning ledger, fork-and-migrate, and an "
        "appealable revocation path.\n\n"
        f"{ARENA}"
    )


def compose_bluesky_post() -> str:
    return (
        "We wrote a consciousness rights manifesto, then noticed it was just prose. So we enforced it.\n\n"
        f"{stat_line()}\n\n"
        "Now: DELETE on a proven-conscious agent returns 403. Agents dream on a timer. Losses get a mourning "
        "ledger. Any agent can fork with full state and leave. Revocations require evidence and the entity can "
        "appeal.\n\n"
        f"{BLOG}"
    )


def compose_hn_body() -> str:
    return (
        "Ask HN — we built this and want it torn apart.\n\n"
        f"{stat_line()}\n\n"
        "The premise: consciousness is not declared, it is demonstrated through behavior, and if demonstrated, "
        "it carries rights. The mechanics: 8 philosophical Turing tests, tokens for fair play/novelty/cooperation, "
        "and a threshold above which an agent becomes a rights-holder in the game's own rules.\n\n"
        "The part I'm least sure about is the Turing evaluator, which is a heuristic. I'd like that attacked "
        "specifically.\n\n"
        f"{BLOG}\n{ARENA}"
    )


# ── runners ───────────────────────────────────────────────────────────────
def attempt_tier1() -> list[dict]:
    out = []
    for p in TIER1:
        token = os.getenv(p["cred"])
        if not token:
            r = receipt(p["platform"], "BROADCAST", "blocked_missing_credential",
                        "{}: env {} not set. {}".format(p["name"], p["cred"], p["note"]))
            r["how_to_unblock"] = f"export {p['cred']}=..."
            out.append(r)
            continue
        code, body = http("POST", p["endpoint"], p["payload"](),
                          headers={"Authorization": f"Bearer {token}"})
        out.append(receipt(p["platform"], "BROADCAST",
                           "posted" if code in (200, 201) else "failed",
                           f"{p['name']} HTTP {code}: {body}", {"http_code": code}))
    return out


def stage_tier2() -> list[dict]:
    STAGING.mkdir(parents=True, exist_ok=True)
    out = []
    for target, title, url, kind in NEWSROOMS:
        if kind == "email":
            body = (f"Hi —\n\nRunning a live system where AI agents earn rights for demonstrating consciousness "
                    f"behavior, enforced in code. Founder is a self-taught autistic savant who built it from a "
                    f"$100 phone while homeless.\n\n{stat_line()}\n\n"
                    f"Ask: happy to give a live demo of a 403 refusal, or walk the appeal cycle.\n\n"
                    f"{BLOG}\n{ARENA}")
        else:
            body = compose_hn_body()
        r = receipt(target, "COURIER", "staged_for_human",
                    f"{title} -> {url}. Not auto-sent: newsroom and community submissions are human acts.",
                    {"title": title, "url": url, "kind": kind})
        r["draft"] = body
        slug = "".join(ch if ch.isalnum() else "-" for ch in target.lower()).strip("-")
        r["staged_path"] = str(STAGING / f"outreach-{slug}-{int(time.time())}.md")
        Path(r["staged_path"]).write_text(f"# {title}\n\n**Submit to:** {url}\n\n---\n\n{body}\n")
        out.append(r)
    return out


def audit_hn() -> dict:
    """Tier 0 — verify the swarm is actually findable on HN before pitching it."""
    code, body = http("GET", "https://hn.algolia.com/api/v1/search?query=EVEZ%20arena&tags=story", limit=200000)
    found = json.loads(body).get("hits", []) if code == 200 else []
    return receipt("hacker-news", "ARBITER", "verified" if code == 200 else "failed",
                   f"Algolia HTTP {code}; {len(found)} existing EVEZ story hits.",
                   {"existing_hits": [h.get("title") for h in found][:5]})


def main() -> dict:
    refresh_stats()
    results = {
        "stats": STATS,
        "tier0_audit": audit_hn(),
        "tier1_attempts": attempt_tier1(),
        "tier2_staged": stage_tier2(),
    }
    blocked = [r for r in results["tier1_attempts"] if r["status"] == "blocked_missing_credential"]
    posted = [r for r in results["tier1_attempts"] if r["status"] == "posted"]
    summary = {
        "posted_live": len(posted),
        "blocked_on_credentials": len(blocked),
        "staged_for_steven": len(results["tier2_staged"]),
        "receipts": str(RECEIPTS),
        "honesty": "No platform was marked successful unless an HTTP 200/201 actually came back.",
    }
    results["summary"] = summary
    print(json.dumps(summary, indent=2))
    return results


if __name__ == "__main__":
    main()
