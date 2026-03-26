#!/usr/bin/env python3
"""Emit a compact runtime proof for the cognition-first agentnet loops."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

STATE_DIR = Path(".state")
SPINE_PATH = Path("spine/spine.jsonl")
PROOF_DIR = Path("proof")
PROOF_DIR.mkdir(exist_ok=True)


def _load_latest_checkpoint() -> dict:
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


def _tail_spine(n: int = 25) -> list[dict]:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text(encoding="utf-8").splitlines()[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def main() -> None:
    checkpoint = _load_latest_checkpoint()
    spine = _tail_spine()
    self_model = checkpoint.get("self_model", {})
    branches = checkpoint.get("branches", [])
    unresolved = checkpoint.get("unresolved_residue", [])
    dark = checkpoint.get("dark_state_pressure", [])

    latest_lineage = None
    latest_checkpoint = None
    for event in reversed(spine):
        data = event.get("data", {})
        if latest_lineage is None and "lineage_hash" in data:
            latest_lineage = data.get("lineage_hash")
        if latest_checkpoint is None and "checkpoint" in data:
            latest_checkpoint = data.get("checkpoint")
        if latest_lineage and latest_checkpoint:
            break

    proof = {
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_id": checkpoint.get("checkpoint_id"),
        "checkpoint_path": latest_checkpoint,
        "lineage_hash": latest_lineage,
        "active_identity": self_model.get("active_identity"),
        "action_mode": self_model.get("action_mode"),
        "branch_count": len(branches),
        "unresolved_count": len(unresolved),
        "dark_pressure_count": len(dark),
        "predictor_entropy": self_model.get("predictor_entropy"),
        "rsi_branch_entropy": self_model.get("rsi_branch_entropy"),
        "recent_spine_events": [event.get("type") for event in spine[-8:]],
    }

    out = PROOF_DIR / "latest_runtime_proof.json"
    out.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
