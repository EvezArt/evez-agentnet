#!/usr/bin/env python3
"""Cognition-aware predictor for evez-agentnet.

Returns ranked plans plus a compact uncertainty ledger so rival futures survive.
"""

from __future__ import annotations

import json
import logging
from math import log as _math_log
from pathlib import Path
from typing import Any

from .predict_agent import _generate_action_plan, _score_signal

# NOTE: must not be named `log` — that name collides with `from math import log`
# below and makes every _entropy() call raise `TypeError: 'Logger' object is
# not callable`. That crash killed the canonical supervised boot path on every
# start. Logger is `_logger`; the math function keeps the plain name.
_logger = logging.getLogger("agentnet.cognition_predictor")


def _entropy(scores: list[float], k: int = 3) -> float:
    """CUT-SEPARABILITY entropy: is the ship/drop boundary decisive?

    The generator drafts the top-K (K=3) signals and the shipper publishes
    those drafts. A tie between #1 and #2 is harmless there -- any of the
    tied candidates is an equally defensible pick. What actually matters
    is the CUT: can we distinguish the last shipped signal from the first
    dropped one?

      cut_gap = s[K-1] - s[K]   (3rd vs 4th ranked)
      span    = s[0]   - s[K]
      entropy = 1 - cut_gap/span
        0.0 -> decisive cut, shipping selection is defensible (gate opens)
        1.0 -> the boundary is a coin flip (gate closes)
    """
    if len(scores) <= k:
        return 0.0  # nothing is dropped; there is no ambiguous boundary
    s = sorted(scores, reverse=True)
    cut_gap = s[k - 1] - s[k]
    span = s[0] - s[k]
    if span <= 1e-9:
        return 1.0 if cut_gap <= 1e-9 else 0.0
    return max(0.0, min(1.0, 1.0 - cut_gap / span))


def run(scan_results: list) -> dict[str, Any]:
    if not scan_results:
        return {"ranked": [], "uncertainty": {"entropy": 0.0, "rival_count": 0, "top_rivals": []}}

    scored = []
    for item in scan_results:
        enriched = dict(item)
        enriched["opportunity_score"] = _score_signal(enriched)
        scored.append(enriched)

    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)
    top = scored[:5]
    plans = [_generate_action_plan(item) for item in top]

    rival_count = max(0, len(top) - 1)
    entropy = _entropy([item["opportunity_score"] for item in top])
    top_rivals = [
        {
            "title": item.get("title", "Untitled"),
            "source": item.get("source", ""),
            "opportunity": item.get("opportunity", ""),
            "opportunity_score": item.get("opportunity_score", 0.0),
        }
        for item in top[1:4]
    ]

    payload = {
        "ranked": plans,
        "uncertainty": {
            "entropy": entropy,
            "rival_count": rival_count,
            "top_rivals": top_rivals,
        },
    }

    out = Path("predictor/predictions_cognition.jsonl")
    out.parent.mkdir(exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

    return payload
