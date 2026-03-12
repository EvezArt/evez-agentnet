#!/usr/bin/env python3
"""
reporter.py — Agent status reporter.

Polls all active agents, collects status, emails digest to rubikspubes69@gmail.com
and logs to evez-autonomous-ledger.

Run: python3 agents/reporter.py
Or: import and call report()
"""

import json
import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SPINE_FILE = Path("spine/spine.jsonl")
REPORT_FILE = Path("spine/last_report.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def collect_agent_status() -> dict:
    """Collect status from all known agent modules."""
    status = {
        "timestamp": _now(),
        "agents": {},
        "queue": {"pending": 0},
        "spine": {"event_count": 0, "last_hash": "none"},
    }

    # Spine stats
    if SPINE_FILE.exists():
        lines = [l for l in SPINE_FILE.read_text().strip().splitlines() if l]
        status["spine"]["event_count"] = len(lines)
        if lines:
            last = json.loads(lines[-1])
            status["spine"]["last_hash"] = last.get("hash", "none")[:16]

    # Queue stats
    queue_file = Path("spine/review_queue.jsonl")
    if queue_file.exists():
        items = [json.loads(l) for l in queue_file.read_text().strip().splitlines() if l]
        status["queue"]["pending"] = sum(1 for i in items if i.get("status") == "pending")
        status["queue"]["total"] = len(items)

    # Known agent modules
    for agent_name in ["scanner", "predictor", "generator", "accumulator"]:
        agent_file = Path(f"agents/{agent_name}.py")
        status["agents"][agent_name] = {
            "exists": agent_file.exists(),
            "size_bytes": agent_file.stat().st_size if agent_file.exists() else 0,
        }

    return status


def format_digest(status: dict) -> str:
    """Format status as email body."""
    lines = [
        f"EVEZ AGENTNET STATUS — {status['timestamp']}",
        "=" * 50,
        "",
        "SPINE:",
        f"  Events: {status['spine']['event_count']}",
        f"  Last hash: {status['spine']['last_hash']}",
        "",
        "REVIEW QUEUE:",
        f"  Pending approvals: {status['queue'].get('pending', 0)}",
        f"  Total items: {status['queue'].get('total', 0)}",
        "",
        "AGENT MODULES:",
    ]
    for name, info in status["agents"].items():
        exists = "✓" if info["exists"] else "✗"
        lines.append(f"  {exists} {name}: {info['size_bytes']} bytes")

    lines += [
        "",
        "Ledger: https://github.com/EvezArt/evez-autonomous-ledger",
        "Ops: https://evez666.slack.com/archives/C0AL8E1B55J",
    ]
    return "\n".join(lines)


def report():
    """Main report function. Collect, format, save, and optionally email."""
    status = collect_agent_status()
    digest = format_digest(status)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(status, indent=2))

    print(digest)
    print(f"\n[REPORTER] Report saved to {REPORT_FILE}")
    return status, digest


if __name__ == "__main__":
    report()
