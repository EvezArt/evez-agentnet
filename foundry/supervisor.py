#!/usr/bin/env python3
"""Select the next bounded Foundry action from observed evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

PRIORITY = [
    ("BOOT_FAILURE", "REPAIR_GENERATED_OS"),
    ("ADVERSARY_FAILURE", "REPAIR_SECURITY_BOUNDARY"),
    ("REPLICATION_FAILURE", "INVESTIGATE_NONDETERMINISM"),
    ("HERMES_ERROR", "VERIFY_HERMES_INTERFACE"),
    ("OPENCLAW_ERROR", "VERIFY_OPENCLAW_INTERFACE"),
]

def choose(result: dict) -> dict:
    text = json.dumps(result, ensure_ascii=False).upper()
    for marker, action in PRIORITY:
        if marker in text:
            return {"action": action, "reason": marker, "authority": 5}
    checks = result.get("checks", {})
    for name, check in checks.items():
        if isinstance(check, dict) and check.get("status") == "FAIL":
            return {"action": "INVESTIGATE_" + name.upper(), "reason": "failed check", "authority": 5}
    return {
        "action": "DISCOVER_NEXT_CAPABILITY",
        "reason": "current bounded cycle has no recorded failure",
        "authority": 5,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    next_action = choose(result)
    payload = {
        "schema": "evez.next-action.v1",
        "source_result": str(Path(args.result).resolve()),
        "next_action": next_action,
        "status": "PROPOSED",
        "rule": "failure evidence outranks novelty; unknowns remain unknown",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
