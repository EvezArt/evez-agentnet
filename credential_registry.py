#!/usr/bin/env python3
"""
Credentials the EVEZ stack expects, and where to get each one.

This file is the single place that records which secret goes where. It
contains NO secret values — only names, where the value belongs, and what
breaks if it is missing.

WHY THIS EXISTS

Two live credentials are currently exposed in PUBLIC repositories:

  1. Supabase service_role key — public in EvezArt/evez-atlas
     (functions/evezCorpusStore.ts, functions/evezPersist.ts)
     service_role BYPASSES row-level security. Full DB read/write.

  2. ClawHub token (clh_...) — public in EvezArt/evez-atlas
     (evez-os-sensors/self_interrogation.py)
     Sent live to clawhub.ai/api/skills from committed source.

Neither can be fixed from here: rotation happens at the provider, and only
the custodian can do it. What CAN be fixed now is the second half of the
problem — making sure the next rotation does not immediately get
re-committed. That is what the env-var wiring below does.

Order of operations, and it matters:

  1. ROTATE at the provider first.
  2. THEN set the new value in the runtime environment.
  3. THEN confirm the hardcoded literal is gone from the source.

Doing 3 before 1 leaves the old key live and readable. Doing 1 before 2
means a gap where nothing works. Rotate first.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REGISTRY = [
    {
        "name": "TYPESAFE_API_KEY",
        "purpose": "Jev / System One decision layer (jev_client.py)",
        "where": "https://typesafe.ai — limited early access",
        "stored_in_env": True,
        "wired": True,
        "if_missing": "Jev decisions return an explicit fallback; the "
                      "pipeline is unaffected. Never fabricates a probability.",
    },
    {
        "name": "TWITTER_BEARER_TOKEN",
        "purpose": "Ship twitter_thread drafts",
        "where": "developer.twitter.com — app keys",
        "stored_in_env": False,
        "wired": True,
        "if_missing": "shipper reports channel_not_configured per draft",
    },
    {
        "name": "MASTODON_BASE_URL + MASTODON_ACCESS_TOKEN",
        "purpose": "Ship to Mastodon",
        "where": "any Mastodon instance, read-write scope",
        "stored_in_env": False,
        "wired": True,
        "if_missing": "shipper reports channel_not_configured per draft",
    },
    {
        "name": "GUMROAD_API_KEY",
        "purpose": "Create real Gumroad products (the revenue path)",
        "where": "gumroad.com API settings",
        "stored_in_env": False,
        "wired": True,
        "if_missing": "products stay as drafts for manual upload",
    },
    {
        "name": "STRIPE_SECRET_KEY",
        "purpose": "Payments. Currently a TEMPLATE — .vault.env is empty.",
        "where": "dashboard.stripe.com — API keys",
        "stored_in_env": False,
        "wired": False,
        "if_missing": "revenue is structurally $0.00. This is the single "
                      "hardest blocker to earning anything.",
    },
    {
        "name": "OPENROUTER_API_KEY",
        "purpose": "LLM-backed draft generation",
        "where": "openrouter.ai/keys",
        "stored_in_env": True,
        "wired": True,
        "if_missing": "generators fall back to deterministic templates, "
                      "so drafts are still produced",
    },
    {
        "name": "TELEGRAM_BOT_TOKEN",
        "purpose": "Delivery + alerting",
        "where": "@BotFather",
        "stored_in_env": False,
        "wired": True,
        "if_missing": "shipper cannot deliver; notify.py cannot alert",
    },
]

EXPOSED = [
    {
        "id": "supabase-service-role",
        "severity": "HIGH",
        "public_in": "EvezArt/evez-atlas",
        "paths": ["functions/evezCorpusStore.ts",
                  "functions/evezPersist.ts"],
        "why": "service_role bypasses row-level security entirely",
        "rotate_at": "Supabase dashboard -> Project Settings -> API",
        "also": "audit auth logs for service_role use from unknown IPs; "
                "the JWT claims exp 2036-03-19, a 10-year lifetime",
    },
    {
        "id": "clawhub-token",
        "severity": "HIGH",
        "public_in": "EvezArt/evez-atlas",
        "paths": ["evez-os-sensors/self_interrogation.py"],
        "why": "sent as Authorization: Bearer to clawhub.ai/api/skills "
               "from committed source",
        "rotate_at": "ClawHub account settings",
        "also": "replace the literal with $CLAWHUB_TOKEN env reference",
    },
]


def present() -> dict[str, bool]:
    return {r["name"]: bool(os.environ.get(r["name"], "").strip())
            for r in REGISTRY if " " not in r["name"]}


def report() -> dict:
    p = present()
    return {
        "configured": sorted(k for k, v in p.items() if v),
        "missing": sorted(k for k, v in p.items() if not v),
        "unwired": [r["name"] for r in REGISTRY if not r["wired"]],
        "exposed_credentials": EXPOSED,
        "rotation_order": [
            "1. rotate at the provider",
            "2. set the new value in the runtime environment",
            "3. confirm the hardcoded literal is gone from source",
        ],
    }


def main() -> int:
    r = report()
    print("CONFIGURED :", ", ".join(r["configured"]) or "none")
    print("MISSING    :", ", ".join(r["missing"]) or "none")
    print("UNWIRED    :", ", ".join(r["unwired"]) or "none")
    print()
    print("STILL EXPOSED IN PUBLIC REPOS")
    for e in EXPOSED:
        print(f"  [{e['severity']}] {e['id']}")
        print(f"      repo : {e['public_in']}")
        for path in e["paths"]:
            print(f"      file : {path}")
        print(f"      why  : {e['why']}")
        print(f"      fix  : rotate at {e['rotate_at']}")
        print(f"      also : {e['also']}")
    print()
    print("ROTATION ORDER (doing these out of order leaves a window)")
    for i, s in enumerate(r["rotation_order"], 1):
        print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
