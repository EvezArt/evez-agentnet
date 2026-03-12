#!/usr/bin/env python3
"""
review_queue.py — Human-in-the-loop gate.

Replaces ship() as the final stage of the pipeline.
No action leaves this system without a human_approve event in the spine.

Pipeline:
  scan -> predict -> generate -> review_queue -> human_approve -> dispatch/log
"""

import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Literal

QUEUE_FILE = Path("spine/review_queue.jsonl")
SPINE_FILE = Path("spine/spine.jsonl")

Status = Literal["pending", "approved", "rejected", "expired"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _prev_hash() -> str:
    """Get hash of last spine event."""
    if not SPINE_FILE.exists():
        return "0" * 64
    lines = SPINE_FILE.read_text().strip().splitlines()
    if not lines:
        return "0" * 64
    last = json.loads(lines[-1])
    return last.get("hash", "0" * 64)


@dataclass
class QueueItem:
    item_id: str
    timestamp: str
    agent_id: str
    action_type: str
    payload: dict
    status: Status
    review_required: bool
    expires_at: Optional[str]
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    spine_event_hash: Optional[str] = None


class ReviewQueue:
    """
    Append-only human-in-the-loop gate.

    Every generated action lands here first.
    Nothing dispatches without a human_approve event.
    All decisions are logged to spine.
    """

    def __init__(self):
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SPINE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, agent_id: str, action_type: str, payload: dict,
               ttl_seconds: int = 3600) -> QueueItem:
        """Submit an action for human review. Returns the queued item."""
        item_id = _hash(f"{agent_id}{action_type}{_now()}")[:16]
        expires_at = datetime.fromtimestamp(
            time.time() + ttl_seconds, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        item = QueueItem(
            item_id=item_id,
            timestamp=_now(),
            agent_id=agent_id,
            action_type=action_type,
            payload=payload,
            status="pending",
            review_required=True,
            expires_at=expires_at,
        )

        self._append_queue(item)
        self._log_spine("review_queue_submit", item)
        print(f"[QUEUE] Submitted {item_id} | {action_type} | awaiting human approval")
        return item

    def approve(self, item_id: str, approved_by: str = "human") -> QueueItem:
        """Approve a queued item. Logs to spine. Returns updated item."""
        item = self._get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        if item.status != "pending":
            raise ValueError(f"Item {item_id} is {item.status}, not pending")

        item.status = "approved"
        item.approved_by = approved_by
        item.approved_at = _now()

        self._log_spine("review_queue_approved", item)
        print(f"[QUEUE] Approved {item_id} by {approved_by}")
        return item

    def reject(self, item_id: str, reason: str, rejected_by: str = "human") -> QueueItem:
        """Reject a queued item."""
        item = self._get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        item.status = "rejected"
        item.rejection_reason = reason
        item.approved_by = rejected_by
        item.approved_at = _now()

        self._log_spine("review_queue_rejected", item)
        print(f"[QUEUE] Rejected {item_id}: {reason}")
        return item

    def list_pending(self) -> list[QueueItem]:
        """Return all pending items."""
        return [i for i in self._load_all() if i.status == "pending"]

    def _get(self, item_id: str) -> Optional[QueueItem]:
        for item in self._load_all():
            if item.item_id == item_id:
                return item
        return None

    def _load_all(self) -> list[QueueItem]:
        if not QUEUE_FILE.exists():
            return []
        items = []
        for line in QUEUE_FILE.read_text().strip().splitlines():
            if line:
                d = json.loads(line)
                items.append(QueueItem(**d))
        return items

    def _append_queue(self, item: QueueItem):
        with open(QUEUE_FILE, "a") as f:
            f.write(json.dumps(asdict(item)) + "\n")

    def _log_spine(self, event_type: str, item: QueueItem):
        prev = _prev_hash()
        event = {
            "event_id": _hash(f"{event_type}{item.item_id}{_now()}")[:16],
            "timestamp": _now(),
            "event_type": event_type,
            "agent_id": item.agent_id,
            "action_type": item.action_type,
            "item_id": item.item_id,
            "status": item.status,
            "approved_by": item.approved_by,
            "prev_hash": prev,
        }
        event["hash"] = _hash(json.dumps(event, sort_keys=True))
        item.spine_event_hash = event["hash"]
        with open(SPINE_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    q = ReviewQueue()

    if len(sys.argv) < 2:
        pending = q.list_pending()
        print(f"Pending items: {len(pending)}")
        for p in pending:
            print(f"  {p.item_id} | {p.action_type} | {p.agent_id} | expires {p.expires_at}")
    elif sys.argv[1] == "approve" and len(sys.argv) > 2:
        item = q.approve(sys.argv[2])
        print(f"Approved: {item.item_id}")
    elif sys.argv[1] == "reject" and len(sys.argv) > 3:
        item = q.reject(sys.argv[2], sys.argv[3])
        print(f"Rejected: {item.item_id}")
    elif sys.argv[1] == "submit":
        item = q.submit("cli", "test_action", {"test": True})
        print(f"Submitted: {item.item_id}")
