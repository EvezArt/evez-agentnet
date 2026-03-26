#!/usr/bin/env python3
"""Generate a lightweight HTML dashboard from the latest cognition proof/state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path('.state')
SPINE_PATH = Path('spine/spine.jsonl')
PROOF_PATH = Path('proof/latest_runtime_proof.json')
PROOF_DIR = Path('proof')
PROOF_DIR.mkdir(exist_ok=True)
DASHBOARD_PATH = PROOF_DIR / 'latest_runtime_dashboard.html'


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


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


def _tail_spine(n: int = 20) -> list[dict]:
    if not SPINE_PATH.exists():
        return []
    lines = SPINE_PATH.read_text(encoding='utf-8').splitlines()[-n:]
    return [json.loads(line) for line in lines if line.strip()]


def _metric_card(title: str, value: object) -> str:
    return f"<div class='card'><div class='label'>{title}</div><div class='value'>{value}</div></div>"


def main() -> None:
    proof = _load_json(PROOF_PATH)
    checkpoint = _load_latest_checkpoint()
    spine = _tail_spine()
    self_model = checkpoint.get('self_model', {})
    identities = checkpoint.get('identities', [])

    cards = [
        _metric_card('Active Identity', proof.get('active_identity') or self_model.get('active_identity') or 'unknown'),
        _metric_card('Action Mode', proof.get('action_mode') or self_model.get('action_mode') or 'unknown'),
        _metric_card('Branch Count', proof.get('branch_count', len(checkpoint.get('branches', [])))),
        _metric_card('Unresolved Count', proof.get('unresolved_count', len(checkpoint.get('unresolved_residue', [])))),
        _metric_card('Dark Pressure Count', proof.get('dark_pressure_count', len(checkpoint.get('dark_state_pressure', [])))),
        _metric_card('Predictor Entropy', proof.get('predictor_entropy', self_model.get('predictor_entropy', 'n/a'))),
        _metric_card('RSI Branch Entropy', proof.get('rsi_branch_entropy', self_model.get('rsi_branch_entropy', 'n/a'))),
        _metric_card('Lineage Hash', proof.get('lineage_hash', 'n/a')),
    ]

    identity_rows = ''.join(
        f"<tr><td>{item.get('name')}</td><td>{item.get('stability')}</td><td>{item.get('coherence_gain')}</td><td>{item.get('control_gain')}</td><td>{item.get('contradiction_load')}</td></tr>"
        for item in identities
    )
    spine_rows = ''.join(
        f"<tr><td>{event.get('ts', '')}</td><td>{event.get('type', '')}</td><td><code>{json.dumps(event.get('data', {}))[:220]}</code></td></tr>"
        for event in spine[-8:]
    )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>evez-agentnet cognition dashboard</title>
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
  <h1>evez-agentnet cognition dashboard</h1>
  <div class='muted'>Generated at {datetime.now(timezone.utc).isoformat()}</div>
  <div class='grid'>
    {''.join(cards)}
  </div>
  <h2>Identity Attractors</h2>
  <table>
    <tr><th>Name</th><th>Stability</th><th>Coherence Gain</th><th>Control Gain</th><th>Contradiction Load</th></tr>
    {identity_rows}
  </table>
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
