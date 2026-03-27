#!/usr/bin/env python3
"""Emit governed artifacts from existing agentnet runtime outputs.

Reads:
- worldsim/worldsim_state.json
- spine/spine.jsonl

Writes:
- status/system-state.json
- status/execution-integrity.json
- status/artifact-contract.json

This binds the existing runtime to the schema layer without rewriting the orchestrator.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'worldsim' / 'worldsim_state.json'
SPINE_PATH = ROOT / 'spine' / 'spine.jsonl'
STATUS_DIR = ROOT / 'status'
STATUS_DIR.mkdir(exist_ok=True)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {
            'round': 0,
            'total_earned_usd': 0.0,
            'agents': {},
        }
    return json.loads(STATE_PATH.read_text())


def load_spine_tail() -> tuple[int, dict | None]:
    if not SPINE_PATH.exists():
        return 0, None
    lines = [line for line in SPINE_PATH.read_text().splitlines() if line.strip()]
    if not lines:
        return 0, None
    return len(lines), json.loads(lines[-1])


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ''
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit() -> None:
    state = load_state()
    spine_count, last_spine = load_spine_tail()
    timestamp = iso_now()

    last_event_hash = None
    if isinstance(last_spine, dict):
        last_event_hash = last_spine.get('sha256')

    system_state = {
        'schema_version': '1.0.0',
        'state_id': f"agentnet-round-{state.get('round', 0)}",
        'system': 'evez-agentnet',
        'component': 'orchestrator',
        'timestamp': timestamp,
        'status': 'nominal' if state.get('round', 0) > 0 else 'paused',
        'mode': 'construct',
        'metrics': {
            'round': state.get('round', 0),
            'total_earned_usd': state.get('total_earned_usd', 0.0),
            'spine_events': spine_count,
            'agent_count': len(state.get('agents', {})),
        },
        'notes': ['Derived from worldsim state and append-only spine.']
    }

    execution_integrity = {
        'schema_version': '1.0.0',
        'execution_id': f"round-{state.get('round', 0)}",
        'timestamp': timestamp,
        'outcome': 'passed' if last_event_hash else 'degraded',
        'checks': [
            {
                'name': 'worldsim_state_present',
                'status': 'passed' if STATE_PATH.exists() else 'warning',
                'details': str(STATE_PATH)
            },
            {
                'name': 'spine_present',
                'status': 'passed' if SPINE_PATH.exists() else 'warning',
                'details': str(SPINE_PATH)
            },
            {
                'name': 'last_spine_hash_present',
                'status': 'passed' if last_event_hash else 'warning',
                'details': str(last_event_hash)
            }
        ],
        'runtime': 'python',
        'transform_hash': sha256_file(ROOT / 'orchestrator.py'),
        'event_hash': last_event_hash or ''
    }

    artifact_contract = {
        'schema_version': '1.0.0',
        'artifact_id': f"artifact-round-{state.get('round', 0)}",
        'artifact_type': 'status_bundle',
        'timestamp': timestamp,
        'producer': 'orchestration/emit_governed_artifacts.py',
        'path': 'status/',
        'content_hash': sha256_file(STATE_PATH),
        'lineage': {
            'execution_id': execution_integrity['execution_id'],
            'event_hash': execution_integrity['event_hash']
        },
        'labels': ['governed', 'status', 'schema-bound']
    }

    (STATUS_DIR / 'system-state.json').write_text(json.dumps(system_state, indent=2) + '\n')
    (STATUS_DIR / 'execution-integrity.json').write_text(json.dumps(execution_integrity, indent=2) + '\n')
    (STATUS_DIR / 'artifact-contract.json').write_text(json.dumps(artifact_contract, indent=2) + '\n')


if __name__ == '__main__':
    emit()
