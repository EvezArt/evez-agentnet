"""
agents/accumulator.py — evez-agentnet
Tracks earnings per agent per day. Persists to logs/accumulator.jsonl.
Exposes get_summary() used by status API and email reporter.
"""

import json
import time
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

ACC_LOG = Path("logs/accumulator.jsonl")
ACC_LOG.parent.mkdir(exist_ok=True)


def record(agent_id: str, earned_usd: float, task: str = ""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent_id,
        "earned_usd": earned_usd,
        "task": task,
    }
    with open(ACC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_summary() -> dict:
    if not ACC_LOG.exists():
        return {"total": 0.0, "today": 0.0, "by_agent": {}, "last_entries": []}
    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    today_total = 0.0
    by_agent: dict[str, float] = defaultdict(float)
    entries = []
    with open(ACC_LOG) as f:
        for line in f:
            try:
                e = json.loads(line)
                amt = float(e.get("earned_usd", 0))
                total += amt
                by_agent[e["agent"]] += amt
                if e["ts"][:10] == today:
                    today_total += amt
                entries.append(e)
            except Exception:
                pass
    return {
        "total": round(total, 4),
        "today": round(today_total, 4),
        "by_agent": {k: round(v, 4) for k, v in by_agent.items()},
        "last_entries": entries[-10:],
    }
