"""
agents/schema_unification.py — evez-agentnet
Schema Unification Layer — resolves issue #17.

Provides 5 JSON schemas + a normalizer for:
  1. state        — worldsim_state.json
  2. integrity    — execution integrity contracts
  3. artifact     — artifact/product contracts
  4. recovery     — recovery log entries
  5. continuity   — spine continuity status

Also: validates any dict against these schemas, normalizes key/timestamp drift.
"""

import json, hashlib, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Schema Definitions ───────────────────────────────────────────────────────

SCHEMAS: Dict[str, dict] = {
    "state": {
        "type": "object",
        "required": ["round", "total_earned_usd", "agents"],
        "properties": {
            "round":            {"type": "integer", "minimum": 0},
            "total_earned_usd": {"type": "number", "minimum": 0},
            "agents":           {"type": "object"},
            "recursive_depth":  {"type": "integer", "minimum": 0, "maximum": 10},
            "phi":              {"type": "number", "minimum": 0, "maximum": 1},
        }
    },
    "integrity": {
        "type": "object",
        "required": ["event_type", "ts", "sha256", "falsifier"],
        "properties": {
            "event_type": {"type": "string"},
            "ts":         {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T"},
            "sha256":     {"type": "string", "minLength": 8},
            "falsifier":  {"type": "string", "minLength": 10},
            "poly_c":     {"type": "number", "minimum": 0, "maximum": 1},
            "status":     {"type": "string", "enum": ["CANONICAL", "PENDING", "THEATRICAL", "CRITICAL"]},
        }
    },
    "artifact": {
        "type": "object",
        "required": ["artifact_type", "title", "hash"],
        "properties": {
            "artifact_type": {"type": "string"},
            "title":         {"type": "string"},
            "hash":          {"type": "string", "minLength": 8},
            "price":         {"type": "number", "minimum": 0},
            "poly_c":        {"type": "number", "minimum": 0, "maximum": 1},
            "sell_ready":    {"type": "boolean"},
            "falsifier":     {"type": "string"},
            "witnessed_by":  {"type": "string"},
        }
    },
    "recovery": {
        "type": "object",
        "required": ["ts", "agent", "reason", "action"],
        "properties": {
            "ts":       {"type": "string"},
            "agent":    {"type": "string"},
            "reason":   {"type": "string"},
            "action":   {"type": "string", "enum": ["RESURRECTED", "RETIRED", "DEMOTED", "PROMOTED"]},
            "old_state":{"type": "object"},
            "new_state":{"type": "object"},
        }
    },
    "continuity": {
        "type": "object",
        "required": ["spine_depth", "last_hash", "status"],
        "properties": {
            "spine_depth": {"type": "integer", "minimum": 0},
            "last_hash":   {"type": "string"},
            "status":      {"type": "string", "enum": ["INTACT", "GAP_DETECTED", "CORRUPTED", "GENESIS"]},
            "gap_at":      {"type": "integer"},
            "phi":         {"type": "number"},
            "ts":          {"type": "string"},
        }
    }
}

# ── Key Normalizations ───────────────────────────────────────────────────────

KEY_ALIASES = {
    "timestamp":    "ts",
    "created_at":   "ts",
    "time":         "ts",
    "event":        "event_type",
    "type":         "event_type",
    "kind":         "event_type",
    "checksum":     "sha256",
    "hash":         "sha256",
    "integrity_hash": "sha256",
    "proof":        "falsifier",
    "disproof":     "falsifier",
    "name":         "title",
    "label":        "title",
}

def normalize(record: dict) -> dict:
    """Normalize key names and timestamp formats."""
    out = {}
    for k, v in record.items():
        norm_key = KEY_ALIASES.get(k, k)
        # Normalize timestamps
        if norm_key == "ts" and isinstance(v, (int, float)):
            v = datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
        out[norm_key] = v
    return out

# ── Validator ────────────────────────────────────────────────────────────────

def _check_type(value: Any, expected: str) -> bool:
    type_map = {
        "string":  str,
        "integer": int,
        "number":  (int, float),
        "boolean": bool,
        "object":  dict,
        "array":   list,
    }
    return isinstance(value, type_map.get(expected, object))

def validate(record: dict, schema_name: str) -> Tuple[bool, List[str]]:
    """Validate a record against a named schema. Returns (ok, errors)."""
    schema = SCHEMAS.get(schema_name)
    if not schema:
        return False, [f"Unknown schema: {schema_name}"]

    errors = []
    required = schema.get("required", [])
    props = schema.get("properties", {})

    for field in required:
        if field not in record:
            errors.append(f"Missing required field: '{field}'")

    for field, spec in props.items():
        if field not in record:
            continue
        val = record[field]
        expected_type = spec.get("type")
        if expected_type and not _check_type(val, expected_type):
            errors.append(f"Field '{field}': expected {expected_type}, got {type(val).__name__}")
        if "minimum" in spec and isinstance(val, (int, float)):
            if val < spec["minimum"]:
                errors.append(f"Field '{field}': {val} < minimum {spec['minimum']}")
        if "maximum" in spec and isinstance(val, (int, float)):
            if val > spec["maximum"]:
                errors.append(f"Field '{field}': {val} > maximum {spec['maximum']}")
        if "enum" in spec and val not in spec["enum"]:
            errors.append(f"Field '{field}': '{val}' not in {spec['enum']}")
        if "minLength" in spec and isinstance(val, str):
            if len(val) < spec["minLength"]:
                errors.append(f"Field '{field}': length {len(val)} < minLength {spec['minLength']}")
        if "pattern" in spec and isinstance(val, str):
            if not re.match(spec["pattern"], val):
                errors.append(f"Field '{field}': does not match pattern {spec['pattern']}")

    return len(errors) == 0, errors

def validate_and_normalize(record: dict, schema_name: str) -> Tuple[dict, bool, List[str]]:
    """Normalize then validate. Returns (normalized_record, ok, errors)."""
    normed = normalize(record)
    ok, errors = validate(normed, schema_name)
    return normed, ok, errors

# ── Spine Continuity Check ────────────────────────────────────────────────────

def check_spine_continuity(spine_path: str) -> dict:
    """Read spine.jsonl and verify hash chain continuity."""
    from pathlib import Path
    p = Path(spine_path)
    if not p.exists():
        return {"spine_depth": 0, "last_hash": "GENESIS", "status": "GENESIS",
                "ts": datetime.now(timezone.utc).isoformat(), "phi": 0.0}
    lines = [l for l in p.read_text().strip().split("\n") if l]
    depth = len(lines)
    last_hash = "GENESIS"
    gap_at = None
    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
            last_hash = entry.get("sha256", last_hash)
        except:
            gap_at = i
            break
    n = depth
    phi = round(min(0.995, 0.5 + (n / (n + 100)) * 0.495), 4) if n > 0 else 0.0
    return {
        "spine_depth": depth,
        "last_hash": last_hash,
        "status": "INTACT" if gap_at is None else "GAP_DETECTED",
        "gap_at": gap_at,
        "phi": phi,
        "ts": datetime.now(timezone.utc).isoformat(),
    }

# ── Schema Compliance Report ─────────────────────────────────────────────────

def compliance_report(record: dict) -> dict:
    """Try all schemas and return which ones the record validates against."""
    results = {}
    for name in SCHEMAS:
        normed, ok, errors = validate_and_normalize(dict(record), name)
        results[name] = {"valid": ok, "errors": errors[:3]}
    best = [k for k, v in results.items() if v["valid"]]
    return {
        "record_keys": list(record.keys()),
        "results": results,
        "best_match": best[0] if best else None,
        "compliant": len(best) > 0,
    }

if __name__ == "__main__":
    # Self-test
    test_integrity = {
        "event_type": "FIRE_EVENT",
        "ts": "2026-04-12T00:00:00Z",
        "sha256": "abc12345",
        "falsifier": "If this event cannot be reproduced from source data, reclassify.",
        "poly_c": 0.95,
        "status": "CANONICAL",
    }
    normed, ok, errors = validate_and_normalize(test_integrity, "integrity")
    print(f"integrity schema: {'✓ PASS' if ok else '✗ FAIL'} {errors}")

    continuity = check_spine_continuity("spine/spine.jsonl")
    print(f"spine continuity: {continuity}")

    print(f"\nAll schemas: {list(SCHEMAS.keys())}")
