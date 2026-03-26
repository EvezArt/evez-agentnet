#!/usr/bin/env python3
"""Lightweight runtime status surface for the cognition-first agentnet loops."""

from __future__ import annotations

import json
from pathlib import Path

STATE_DIR = Path(".state")
SPINE_PATH = Path("spine/spine.jsonl")


def load_latest_checkpoint() -> dict:
    latest = STATE_DIR / "latest.json"
    if not latest.exists():
        return {}
    payload = json.loads(latest.read_text(encoding="utf-8"))
    checkpoint_name = payload.get("latest")
    if not checkpoint_name:
        return {}
    checkpoint = STATE_DIR / checkpoint_name
    if not checkpoint.exists():
        return {}
    return json.loads(checkpoint.read_text(encoding="utf-8"))


def tail_spine(n: int = 5) -> list[dict]:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text(encoding="utf-8").splitlines()[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def main() -> None:
    state = load_latest_checkpoint()
    branches = state.get("branches", [])
    unresolved = state.get("unresolved_residue", [])
    dark = state.get("dark_state_pressure", [])
    self_model = state.get("self_model", {})

    summary = {
        "checkpoint_id": state.get("checkpoint_id"),
        "active_identity": self_model.get("active_identity"),
        "action_mode": self_model.get("action_mode"),
        "branch_count": len(branches),
        "unresolved_count": len(unresolved),
        "dark_pressure_count": len(dark),
        "rsi_branch_entropy": self_model.get("rsi_branch_entropy"),
        "predictor_entropy": self_model.get("predictor_entropy"),
        "recent_spine_events": [event.get("type") for event in tail_spine()],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
