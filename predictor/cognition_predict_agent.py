#!/usr/bin/env python3
"""Cognition-aware predictor for evez-agentnet.

Returns ranked plans plus a compact uncertainty ledger so rival futures survive.
"""

from __future__ import annotations

import json
import logging
from math import log
from pathlib import Path
from typing import Any

from .predict_agent import _generate_action_plan, _score_signal

log = logging.getLogger("agentnet.cognition_predictor")


def _entropy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    total = sum(max(s, 1e-6) for s in scores)
    probs = [max(s, 1e-6) / total for s in scores]
    return -sum(p * log(p) for p in probs)


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
