#!/usr/bin/env python3
"""Audit EVEZ forensic material for provenance, chronology, and overclaiming.

Stdlib-only. It does not decide whether a claim is true. It detects when
the repository itself is presenting a claim with insufficient evidence
metadata or when internal artifacts contradict one another.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HIGH_RISK = re.compile(
    r"\b("
    r"confirmed|proved|proven|same actor|same syndicate|same infrastructure|"
    r"not coincidence|cover.?up|criminal enterprise|RICO|OFAC violation|"
    r"legally admissible|admissible|criminal charges warranted|"
    r"99\.1%|100%|623\+|62 million|fixed payouts|188 citations"
    r")\b",
    re.I,
)

TARGETS = [
    ROOT / "docs" / "FBI_IC3_Complaint_DMZHOST.md",
    ROOT / "docs" / "forensic_dossier_standalone.md",
    ROOT / "forge_output" / "wydot-dmzhost-connection-report.md",
    ROOT / "forge_output" / "wydot-dmzhos-coverage-report.html",
]

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def audit_chain(path: Path) -> list[str]:
    if not path.exists():
        return [f"MISSING_CHAIN: {path}"]

    records = []
    errors = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            errors.append(f"INVALID_JSONL: {path}:{line_no}")

    seqs = [r.get("n") for r in records if isinstance(r.get("n"), int)]
    if seqs:
        errors.append(f"CHAIN_RECORDS: {len(records)}")
        errors.append(f"CHAIN_MAX_N: {max(seqs)}")
        if 623 not in seqs:
            errors.append("MISSING_EXPECTED_SEQUENCE: n=623")
        if 624 not in seqs:
            errors.append("MISSING_EXPECTED_SEQUENCE: n=624")
        if seqs != sorted(seqs):
            errors.append("NON_MONOTONIC_SEQUENCE: n values are not ordered ascending")
        dupes = sorted({n for n in seqs if seqs.count(n) > 1})
        if dupes:
            errors.append(f"DUPLICATE_SEQUENCE: {dupes}")

    for i, rec in enumerate(records[1:], 1):
        prev = records[i - 1]
        ph = rec.get("ph")
        prev_h = prev.get("h")
        if ph and prev_h and ph != prev_h:
            errors.append(
                f"PREV_HASH_MISMATCH: record_index={i} ph={ph} previous_h={prev_h}"
            )

    conf1 = [
        r for r in records
        if isinstance(r, dict)
        and r.get("d", {}).get("conf") == 1.0
        and r.get("d", {}).get("source") not in (None, "PRIMARY_RECORD")
    ]
    if conf1:
        errors.append(f"CONF_1_NON_PRIMARY: {len(conf1)} records")

    return errors

def scan_claims(path: Path) -> list[str]:
    text = read_text(path)
    if not text:
        return [f"MISSING_OR_UNREADABLE: {path}"]

    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if HIGH_RISK.search(line):
            hits.append(f"HIGH_RISK_CLAIM: {path}:{line_no}: {line.strip()[:240]}")

    if "June 10, 2019" in text and "May 24, 2026" in text:
        hits.append(f"DATE_CONFLICT: {path}: contains both the 2019 WYDOT incident date and a 2026 incident label")

    if "623+" in text:
        hits.append(f"UNSUPPORTED_COUNT: {path}: contains '623+' without a directly enumerated chain")

    return hits

def security_scan() -> list[str]:
    findings = []
    env = ROOT / ".env"
    if env.exists():
        findings.append("SECRET_FILE_TRACKED: .env exists in the repository")
    return findings

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    findings: list[str] = []
    findings.extend(audit_chain(ROOT / "docs" / "permaaudit-chain.jsonl"))

    for path in TARGETS:
        findings.extend(scan_claims(path))

    findings.extend(security_scan())

    for finding in findings:
        print(f"[AUDIT] {finding}")

    if args.strict and findings:
        return 2

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
