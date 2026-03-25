"""
daemon/spine.py — evez-agentnet
Append-only JSONL event log for all daemon actions.
Resolves: evez-agentnet#15
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SPINE_PATH = Path(os.environ.get("DAEMON_SPINE", "daemon/spine.jsonl"))


def append(event_type: str, data: dict) -> dict:
    SPINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **data,
    }
    with open(SPINE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def tail(n: int = 20) -> list:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text().strip().splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def count() -> int:
    if not SPINE_PATH.exists():
        return 0
    return sum(1 for _ in SPINE_PATH.open())
