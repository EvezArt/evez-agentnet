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

from .ship_agent import SHIP_LOG, _log_ship, run as base_ship_run

log = logging.getLogger("agentnet.cognition_shipper")
GOV_LOG = Path("shipper/cognition_ship_log.jsonl")
GOV_LOG.parent.mkdir(exist_ok=True)

UNRESOLVED_THRESHOLD = 10
ENTROPY_THRESHOLD = 1.0  # cut-entropy: 1.0 == perfect tie == degenerate scan


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

    if predictor_entropy >= ENTROPY_THRESHOLD:
        gate["status"] = "blocked"
        gate["reason"] = "predictor_entropy"
        _log(gate)
        return 0.0, gate

    # Cross-run dedupe: an open gate must not re-post a signal that already
    # shipped (the 783-draft pile was ~30 copies of the same repos). Dedupe
    # key is (type, title) against the append-only ship log.
    import json as _json
    shipped_keys: set = set()
    try:
        with SHIP_LOG.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = _json.loads(line)
                except ValueError:
                    continue
                if row.get("status") == "shipped":
                    shipped_keys.add((row.get("type"), row.get("title")))
    except FileNotFoundError:
        pass
    fresh = [
        d for d in drafts
        if (d.get("type"), d.get("title")) not in shipped_keys
    ]
    gate["deduped"] = len(drafts) - len(fresh)
    gate["draft_count"] = len(drafts)
    drafts = fresh

    if not drafts:
        # Everything deduped away: the gate passed but there is nothing NEW
        # to ship. Honest status is "no_new_work", not a shipped round with
        # zero ships -- the same fake-success class test_shipper_honesty
        # exists to kill.
        gate["status"] = "no_new_work"
        gate["reason"] = "all_drafts_already_shipped"
        gate["earned_usd"] = 0.0
        _log(gate)
        return 0.0, gate

    # base_ship_run's legacy contract: bare float OR summary dict (older
    # shippers). The orchestrator accumulates the float; normalize here so
    # the caller never sees a dict where a float belongs.
    summary = base_ship_run(drafts)
    if isinstance(summary, dict):
        earned = float(summary.get("earned_usd", 0.0) or 0.0)
        gate["shipped"] = summary.get("shipped", 0)
    else:
        earned = float(summary)
        gate["shipped"] = len(drafts) if earned > 0 else 0
    gate["status"] = "shipped"
    gate["reason"] = "passed"
    gate["earned_usd"] = earned
    _log(gate)
    return earned, gate
