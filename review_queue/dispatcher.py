#!/usr/bin/env python3
"""Queue drafts for human review and dispatch only approved items."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

REVIEW_QUEUE_PATH = Path("review_queue/review_queue.jsonl")
APPROVALS_PATH = Path("review_queue/approvals.jsonl")

REVIEW_QUEUE_PATH.parent.mkdir(exist_ok=True)


def _write_jsonl(path: Path, payload: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(payload) + "\n")


def enqueue_for_review(drafts: List[dict], round_id: int) -> list:
    """Persist generated drafts in a queue for operator review."""
    queued = []
    for idx, draft in enumerate(drafts, start=1):
        item = {
            "review_id": f"r{round_id}-d{idx}",
            "round": round_id,
            "status": "pending",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "draft": draft,
        }
        _write_jsonl(REVIEW_QUEUE_PATH, item)
        queued.append(item)
    return queued


def human_approve(queue_items: List[dict]) -> list:
    """Return approved drafts.

    Default is safe: no autonomous approval. To streamline local testing,
    set HUMAN_APPROVAL_MODE=auto to approve every queued item.
    """
    mode = os.getenv("HUMAN_APPROVAL_MODE", "manual").lower()
    approved = []
    if mode != "auto":
        return approved

    for item in queue_items:
        decision = {
            "review_id": item["review_id"],
            "approved": True,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": "env:auto",
        }
        _write_jsonl(APPROVALS_PATH, decision)
        approved.append(item["draft"])
    return approved
