#!/usr/bin/env python3
"""Validate EVEZ acknowledgement records without promoting uncertainty to fact.

Stdlib-only. The validator checks structure and forbidden state promotion.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ALLOWED = {
    "OBSERVED","SUPPORTED","INFERRED","PROPOSED","UNKNOWN",
    "INACCESSIBLE","CONTRADICTED","STALE","RETRACTED"
}
REQUIRED = {
    "id","subject","state","boundary","evidence_refs",
    "timestamp","provenance","resolution_condition","next_experiment"
}

def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/acknowledgements.jsonl")
    if not path.exists():
        print(f"missing: {path}")
        return 2
    errors = 0
    seen = set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"{path}:{n}: invalid JSON: {e}")
            errors += 1
            continue
        missing = REQUIRED - obj.keys()
        if missing:
            print(f"{path}:{n}: missing fields: {sorted(missing)}")
            errors += 1
        if obj.get("state") not in ALLOWED:
            print(f"{path}:{n}: invalid state: {obj.get('state')!r}")
            errors += 1
        ident = obj.get("id")
        if ident in seen:
            print(f"{path}:{n}: duplicate id: {ident}")
            errors += 1
        seen.add(ident)
        if obj.get("state") in {"UNKNOWN","INACCESSIBLE","CONTRADICTED"} and not obj.get("resolution_condition"):
            print(f"{path}:{n}: unresolved state requires resolution_condition")
            errors += 1
        if obj.get("state") == "OBSERVED" and not obj.get("evidence_refs"):
            print(f"{path}:{n}: OBSERVED requires evidence_refs")
            errors += 1
    print(f"acknowledgement-audit: {'PASS' if errors == 0 else 'FAIL'} errors={errors} records={len(seen)}")
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
