#!/usr/bin/env python3
"""Summarize recent spine activity for governed cognition runs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

SPINE_PATH = Path("spine/spine.jsonl")


def main() -> None:
    if not SPINE_PATH.exists():
        print(json.dumps({"rounds": [], "summary": {"events": 0}}, indent=2))
        return

    rounds: dict[int, dict] = defaultdict(lambda: {
        "round": None,
        "modes": set(),
        "events": [],
        "lineage_hashes": set(),
        "checkpoints": set(),
        "predictor_entropy": None,
        "rsi_branch_entropy": None,
        "ship_status": None,
        "ship_reason": None,
    })

    for line in SPINE_PATH.read_text(encoding="utf-8").splitlines()[-200:]:
        if not line.strip():
            continue
        event = json.loads(line)
        data = event.get("data", {})
        rnd = data.get("round")
        if rnd is None:
            continue
        bucket = rounds[rnd]
        bucket["round"] = rnd
        bucket["events"].append(event.get("type"))
        if "mode" in data:
            bucket["modes"].add(data["mode"])
        if "lineage_hash" in data:
            bucket["lineage_hashes"].add(data["lineage_hash"])
        if "checkpoint" in data:
            bucket["checkpoints"].add(data["checkpoint"])
        if "predictor_entropy" in data:
            bucket["predictor_entropy"] = data.get("predictor_entropy")
        if "rsi_branch_entropy" in data:
            bucket["rsi_branch_entropy"] = data.get("rsi_branch_entropy")
        if event.get("type") == "ship_governance":
            bucket["ship_status"] = data.get("status")
            bucket["ship_reason"] = data.get("reason")

    ordered = []
    for rnd in sorted(rounds.keys())[-10:]:
        item = rounds[rnd]
        ordered.append({
            "round": rnd,
            "modes": sorted(item["modes"]),
            "event_count": len(item["events"]),
            "lineage_hash_count": len(item["lineage_hashes"]),
            "checkpoint_count": len(item["checkpoints"]),
            "predictor_entropy": item["predictor_entropy"],
            "rsi_branch_entropy": item["rsi_branch_entropy"],
            "ship_status": item["ship_status"],
            "ship_reason": item["ship_reason"],
            "tail_events": item["events"][-6:],
        })

    payload = {
        "rounds": ordered,
        "summary": {
            "events": sum(item["event_count"] for item in ordered),
            "rounds": len(ordered),
            "blocked_rounds": sum(1 for item in ordered if item.get("ship_status") == "blocked"),
            "shipped_rounds": sum(1 for item in ordered if item.get("ship_status") == "shipped"),
        },
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
