#!/usr/bin/env python3
"""Cognition-governed shipper for evez-agentnet.

Adds governance gates above truth-plane:
- action_mode must permit shipping
- unresolved residue must remain below threshold
- predictor entropy must remain below threshold
- daemon lineage hash is mirrored into the ship log
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ship_agent import run as base_ship_run

log = logging.getLogger("agentnet.cognition_shipper")
GOV_LOG = Path("shipper/cognition_ship_log.jsonl")
GOV_LOG.parent.mkdir(exist_ok=True)

UNRESOLVED_THRESHOLD = 10
ENTROPY_THRESHOLD = 1.2


def _log(entry: dict[str, Any]) -> None:
    with GOV_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def run(
    drafts: list,
    *,
    action_mode: str,
    unresolved_count: int,
    predictor_entropy: float,
    lineage_hash: str,
) -> tuple[float, dict[str, Any]]:
    gate = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action_mode": action_mode,
        "unresolved_count": unresolved_count,
        "predictor_entropy": predictor_entropy,
        "lineage_hash": lineage_hash,
        "draft_count": len(drafts),
    }

    if action_mode not in {"construct", "prepare"}:
        gate["status"] = "blocked"
        gate["reason"] = "action_mode"
        _log(gate)
        return 0.0, gate

    if unresolved_count > UNRESOLVED_THRESHOLD:
        gate["status"] = "blocked"
        gate["reason"] = "unresolved_count"
        _log(gate)
        return 0.0, gate

    if predictor_entropy > ENTROPY_THRESHOLD:
        gate["status"] = "blocked"
        gate["reason"] = "predictor_entropy"
        _log(gate)
        return 0.0, gate

    earned = base_ship_run(drafts)
    gate["status"] = "shipped"
    gate["reason"] = "passed"
    gate["earned_usd"] = earned
    _log(gate)
    return earned, gate
