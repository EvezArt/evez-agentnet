#!/usr/bin/env python3
"""Cognition-aware generator for evez-agentnet.

Prioritizes daemon build-queue artifacts before plain ranked predictions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .generate_agent import _generate_draft

log = logging.getLogger("agentnet.cognition_generator")

BUILD_QUEUE_PATH = Path(".state/build_queue.jsonl")


def _load_queue() -> list[dict[str, Any]]:
    if not BUILD_QUEUE_PATH.exists():
        return []
    with BUILD_QUEUE_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _drain_queue(remaining: list[dict[str, Any]]) -> None:
    BUILD_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BUILD_QUEUE_PATH.open("w", encoding="utf-8") as handle:
        for item in remaining:
            handle.write(json.dumps(item) + "\n")


def _queue_item_to_prediction(item: dict[str, Any]) -> dict[str, Any]:
    label = item.get("label", "queued-artifact")
    notes = item.get("notes", [])
    return {
        "title": label,
        "deliverable_type": "github_post",
        "action_plan": f"Build queued artifact for {label}. Notes: {'; '.join(notes)}",
        "source": "daemon_build_queue",
        "opportunity_score": item.get("priority", 0.0),
    }


def run(predictions: list, truth_plane: str = "CANONICAL") -> list:
    drafts = []
    queue_items = _load_queue()

    consumed = 0
    for item in queue_items[:3]:
        pred = _queue_item_to_prediction(item)
        try:
            draft = _generate_draft(pred, truth_plane)
            if draft:
                draft["queue_origin"] = True
                drafts.append(draft)
                consumed += 1
        except Exception as e:
            log.error("Queued draft failed for %s: %s", pred.get("title", "?"), e)

    if consumed:
        _drain_queue(queue_items[consumed:])

    if len(drafts) >= 3:
        return drafts

    for pred in predictions[: max(0, 3 - len(drafts))]:
        try:
            draft = _generate_draft(pred, truth_plane)
            if draft:
                draft["queue_origin"] = False
                drafts.append(draft)
        except Exception as e:
            log.error("Prediction draft failed for %s: %s", pred.get("title", "?"), e)

    return drafts
