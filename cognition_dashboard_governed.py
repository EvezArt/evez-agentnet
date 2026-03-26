#!/usr/bin/env python3
"""Generate a richer HTML dashboard for the governed cognition runtime."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROOF_DIR = Path('proof')
PROOF_DIR.mkdir(exist_ok=True)
PROOF_PATH = PROOF_DIR / 'latest_runtime_proof.json'
RECEIPT_PATH = PROOF_DIR / 'latest_cognition_receipt.json'
DASHBOARD_PATH = PROOF_DIR / 'latest_governed_dashboard.html'
STATE_DIR = Path('.state')
SPINE_PATH = Path('spine/spine.jsonl')


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def _tail_spine(n: int = 20) -> list[dict]:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text(encoding='utf-8').splitlines()[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def _metric(title: str, value: object) -> str:
    return f"<div class='card'><div class='label'>{title}</div><div class='value'>{value}</div></div>"


def main() -> None:
    proof = _load_json(PROOF_PATH)
    receipt = _load_json(RECEIPT_PATH)
    spine = _tail_spine(16)
    ship_gate = receipt.get('latest_ship_governance', {})

    cards = [
        _metric('Active Identity', receipt.get('active_identity') or proof.get('active_identity') or 'unknown'),
        _metric('Action Mode', receipt.get('action_mode') or proof.get('action_mode') or 'unknown'),
        _metric('Branch Count', receipt.get('branch_count', proof.get('branch_count', 'n/a'))),
        _metric('Unresolved Count', receipt.get('unresolved_count', proof.get('unresolved_count', 'n/a'))),
        _metric('Build Queue Depth', receipt.get('build_queue_depth', 'n/a')),
        _metric('Predictor Entropy', receipt.get('predictor_entropy', proof.get('predictor_entropy', 'n/a'))),
        _metric('RSI Branch Entropy', receipt.get('rsi_branch_entropy', proof.get('rsi_branch_entropy', 'n/a'))),
        _metric('Ship Governance', ship_gate.get('status', 'n/a')),
        _metric('Ship Gate Reason', ship_gate.get('reason', 'n/a')),
        _metric('Lineage Hash', receipt.get('lineage_hash', proof.get('lineage_hash', 'n/a'))),
    ]

    spine_rows = ''.join(
        f"<tr><td>{event.get('ts', '')}</td><td>{event.get('type', '')}</td><td><code>{json.dumps(event.get('data', {}))[:220]}</code></td></tr>"
        for event in spine[-10:]
    )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>evez-agentnet governed dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #0f1115; color: #e7eaf0; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .muted {{ color: #a4acb9; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 20px 0; }}
    .card {{ background: #171b22; border: 1px solid #2b3240; border-radius: 10px; padding: 14px; }}
    .label {{ color: #96a0af; font-size: 12px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: .04em; }}
    .value {{ font-size: 20px; word-break: break-word; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border: 1px solid #2b3240; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #171b22; }}
    code {{ color: #c6d0dd; }}
  </style>
</head>
<body>
  <h1>evez-agentnet governed cognition dashboard</h1>
  <div class='muted'>Generated at {datetime.now(timezone.utc).isoformat()}</div>
  <div class='grid'>{''.join(cards)}</div>
  <h2>Recent Spine Events</h2>
  <table>
    <tr><th>Timestamp</th><th>Type</th><th>Data</th></tr>
    {spine_rows}
  </table>
</body>
</html>
"""
    DASHBOARD_PATH.write_text(html, encoding='utf-8')
    print(str(DASHBOARD_PATH))


if __name__ == '__main__':
    main()
