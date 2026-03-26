#!/usr/bin/env python3
"""Emit a compact governed cognition receipt from checkpoint, spine, queue, and ship logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path('.state')
SPINE_PATH = Path('spine/spine.jsonl')
BUILD_QUEUE_PATH = STATE_DIR / 'build_queue.jsonl'
SHIP_GOV_PATH = Path('shipper/cognition_ship_log.jsonl')
PROOF_DIR = Path('proof')
PROOF_DIR.mkdir(exist_ok=True)
RECEIPT_PATH = PROOF_DIR / 'latest_cognition_receipt.json'


def _tail_jsonl(path: Path, n: int = 1) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding='utf-8').splitlines()[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def _load_latest_checkpoint() -> dict:
    latest = STATE_DIR / 'latest.json'
    if not latest.exists():
        return {}
    payload = json.loads(latest.read_text(encoding='utf-8'))
    checkpoint_name = payload.get('latest')
    if not checkpoint_name:
        return {}
    checkpoint = STATE_DIR / checkpoint_name
    if not checkpoint.exists():
        return {}
    return json.loads(checkpoint.read_text(encoding='utf-8'))


def _build_queue_depth() -> int:
    if not BUILD_QUEUE_PATH.exists():
        return 0
    return len([line for line in BUILD_QUEUE_PATH.read_text(encoding='utf-8').splitlines() if line.strip()])


def main() -> None:
    checkpoint = _load_latest_checkpoint()
    self_model = checkpoint.get('self_model', {})
    recent_spine = _tail_jsonl(SPINE_PATH, 12)
    ship_gate = (_tail_jsonl(SHIP_GOV_PATH, 1) or [{}])[0]

    lineage_hash = None
    checkpoint_path = None
    for event in reversed(recent_spine):
        data = event.get('data', {})
        if lineage_hash is None and 'lineage_hash' in data:
            lineage_hash = data.get('lineage_hash')
        if checkpoint_path is None and 'checkpoint' in data:
            checkpoint_path = data.get('checkpoint')
        if lineage_hash and checkpoint_path:
            break

    receipt = {
        'emitted_at': datetime.now(timezone.utc).isoformat(),
        'checkpoint_id': checkpoint.get('checkpoint_id'),
        'checkpoint_path': checkpoint_path,
        'lineage_hash': lineage_hash,
        'active_identity': self_model.get('active_identity'),
        'action_mode': self_model.get('action_mode'),
        'predictor_entropy': self_model.get('predictor_entropy'),
        'rsi_branch_entropy': self_model.get('rsi_branch_entropy'),
        'branch_count': len(checkpoint.get('branches', [])),
        'unresolved_count': len(checkpoint.get('unresolved_residue', [])),
        'dark_pressure_count': len(checkpoint.get('dark_state_pressure', [])),
        'build_queue_depth': _build_queue_depth(),
        'latest_ship_governance': ship_gate,
        'recent_spine_events': [event.get('type') for event in recent_spine[-8:]],
    }

    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
