#!/usr/bin/env python3
"""Forest verifier — replay every delta ledger in evidence/.

Each ledger chain verifies (SHA-256 links, seq, timestamps, invariants),
AND across the whole forest:
  - subject-state continuity holds GLOBALLY (state_from equals the last
    state_to for that subject in the forest, in chain order);
  - every VERIFIED promotion carries at least one replication record
    in its evidence (MEASURED != REPLICATED);
  - every record carries a falsifier.
Exit 0 only if the entire forest verifies. Wired into CI.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cognition_deltas import DeltaLedger, validate_frontier, validate_transition, DeltaError


def iter_records(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and "hash" in row:
            yield row


def verify_forest(root: Path):
    errors = []
    report = {"ledgers": [], "subjects": {}, "records": 0}
    ledgers = sorted(root.glob("evidence/*/cognition_deltas.jsonl"))
    for path in ledgers:
        ok, errs, count = DeltaLedger(path).verify()
        report["ledgers"].append({"path": str(path), "ok": ok, "records": count,
                                  "errors": errs})
        if not ok:
            errors.extend(f"{path.name}: {e}" for e in errs)

    # Global subject-state continuity, in timestamp order across the forest.
    all_records = []
    for path in ledgers:
        for row in iter_records(path):
            all_records.append((row.get("ts", ""), row, path))
    all_records.sort(key=lambda t: t[0])

    states = {}
    for ts, row, path in all_records:
        report["records"] += 1
        subj = row.get("subject")
        if not subj:
            errors.append(f"{path.name} @{ts}: record without subject")
            continue
        try:
            validate_frontier(row.get("frontier"))
            validate_transition(row.get("state_from"), row.get("state_to"),
                                 row.get("evidence"))
        except DeltaError as exc:
            errors.append(f"{path.name} @{ts} '{subj}': invariant violated: {exc}")
        if subj in states and states[subj] != row.get("state_from"):
            errors.append(
                f"{path.name} @{ts} '{subj}': forest continuity broken — "
                f"is {states[subj]}, claims {row.get('state_from')}")
        states[subj] = row.get("state_to")
        if row.get("state_to") == "VERIFIED":
            reps = ((row.get("evidence") or {}).get("replications")) or []
            if not reps:
                errors.append(
                    f"{path.name} @{ts} '{subj}': VERIFIED without replication")
    report["subjects"] = states
    report["ok"] = not errors
    report["errors"] = errors
    return report


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent)
    report = verify_forest(root)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
