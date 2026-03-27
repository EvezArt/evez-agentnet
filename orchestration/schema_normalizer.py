#!/usr/bin/env python3
"""Schema normalizer for evez-agentnet artifacts.

Normalizes small deviations before validation:
- fills missing schema_version with 1.0.0
- canonicalizes timestamp aliases to ISO-8601 `timestamp`
- maps camelCase keys into snake_case equivalents for known fields
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


KEY_MAP = {
    'schemaVersion': 'schema_version',
    'checkedFiles': 'checked_files',
    'stateId': 'status_id',
}

TIMESTAMP_ALIASES = ('created_at', 'updated_at', 'last_checked', 'time')


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        mapped = KEY_MAP.get(key, key)
        normalized[mapped] = value

    if 'schema_version' not in normalized:
        normalized['schema_version'] = '1.0.0'

    if 'timestamp' not in normalized:
        for alias in TIMESTAMP_ALIASES:
            if alias in normalized:
                normalized['timestamp'] = normalized[alias]
                break
        else:
            normalized['timestamp'] = _iso_now()

    if 'violations' not in normalized:
        normalized['violations'] = []

    if 'checked_files' not in normalized:
        normalized['checked_files'] = 0

    return normalized


if __name__ == '__main__':
    import json, sys

    raw = json.load(sys.stdin)
    print(json.dumps(normalize_payload(raw), indent=2))
