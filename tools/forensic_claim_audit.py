#!/usr/bin/env python3
"""Audit EVEZ forensic material for provenance, chronology, security and overclaiming.

Stdlib-only. The audit distinguishes warnings about historical language from
structural errors that should block publication or deployment.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HIGH_RISK = re.compile(
    r"(?:\b(?:confirmed|proved|proven|same actor|same syndicate|same infrastructure|"
    r"not coincidence|cover.?up|criminal enterprise|RICO|OFAC violation|"
    r"legally admissible|admissible|criminal charges warranted)\b|"
    r"99\.1%|100%|623\+|62 million|fixed payouts|188 citations)",
    re.I,
)

TARGETS = [
    ROOT / "docs" / "FBI_IC3_Complaint_DMZHOST.md",
    ROOT / "docs" / "forensic_dossier_standalone.md",
    ROOT / "forge_output" / "wydot-dmzhost-connection-report.md",
    ROOT / "forge_output" / "wydot-dmzhos-coverage-report.html",
]

HISTORICAL_MARKER = "EVEZ CLAIM STATUS: HISTORICAL_DRAFT"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def audit_chain(path: Path) -> tuple[list[str], int | None]:
    if not path.exists():
        return [f"ERROR:MISSING_CHAIN:{path}"], None

    records: list[dict] = []
    findings: list[str] = []

    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
            if isinstance(record, dict):
                records.append(record)
            else:
                findings.append(
                    f"ERROR:NON_OBJECT_JSONL:{path}:{line_no}"
                )
        except json.JSONDecodeError:
            findings.append(f"ERROR:INVALID_JSONL:{path}:{line_no}")

    seqs = [r.get("n") for r in records if isinstance(r.get("n"), int)]
    max_n = max(seqs) if seqs else None

    if seqs:
        findings.append(f"INFO:CHAIN_RECORDS:{len(records)}")
        findings.append(f"INFO:CHAIN_MAX_N:{max_n}")

        if seqs != sorted(seqs):
            findings.append(
                "WARN:NON_MONOTONIC_SEQUENCE:n values are not ordered ascending; "
                "require an explicit branch_id if this is intentional"
            )

        dupes = sorted({n for n in seqs if seqs.count(n) > 1})
        if dupes:
            findings.append(f"ERROR:DUPLICATE_SEQUENCE:{dupes}")

    for i, rec in enumerate(records[1:], 1):
        prev = records[i - 1]
        ph = rec.get("ph")
        prev_h = prev.get("h")
        if ph and prev_h and ph != prev_h:
            findings.append(
                f"ERROR:PREV_HASH_MISMATCH:record_index={i}"
            )

    conf1 = [
        r
        for r in records
        if isinstance(r, dict)
        and r.get("d", {}).get("conf") == 1.0
        and r.get("d", {}).get("source") not in (None, "PRIMARY_RECORD")
    ]
    if conf1:
        findings.append(f"WARN:CONF_1_NON_PRIMARY:{len(conf1)} records")

    return findings, max_n


def scan_claims(path: Path, chain_max_n: int | None) -> list[str]:
    text = read_text(path)
    if not text:
        return [f"ERROR:MISSING_OR_UNREADABLE:{path}"]

    historical = HISTORICAL_MARKER in text
    hits: list[str] = []

    if not historical:
        for line_no, line in enumerate(text.splitlines(), 1):
            if HIGH_RISK.search(line):
                hits.append(
                    f"WARN:HIGH_RISK_CLAIM:{path}:{line_no}:{line.strip()[:240]}"
                )

    if "June 10, 2019" in text and "May 24, 2026" in text:
        hits.append(
            f"WARN:DATE_CONFLICT:{path}:contains both the 2019 WYDOT incident date "
            "and a 2026 incident label"
        )

    if "623+" in text and (chain_max_n is None or chain_max_n < 623):
        hits.append(
            f"WARN:UNSUPPORTED_COUNT:{path}:contains 623+ while the current public "
            f"chain max is {chain_max_n}"
        )

    if not historical and path.suffix in {".md", ".html"}:
        hits.append(
            f"WARN:PUBLIC_ARTIFACT_UNMARKED:{path}:add "
            "EVEZ CLAIM STATUS: HISTORICAL_DRAFT or convert claims to evidence objects"
        )

    return hits


def security_scan() -> list[str]:
    findings: list[str] = []
    env = ROOT / ".env"
    if env.exists():
        findings.append("ERROR:SECRET_FILE_TRACKED:.env exists in the repository")

    for secret_glob in ("*.pem", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*"):
        for path in ROOT.rglob(secret_glob):
            if ".git" not in path.parts:
                findings.append(f"ERROR:SECRET_ARTIFACT_TRACKED:{path.relative_to(ROOT)}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail only on structural/security errors. Warnings remain visible.",
    )
    args = parser.parse_args()

    findings: list[str] = []
    chain_findings, chain_max_n = audit_chain(ROOT / "docs" / "permaaudit-chain.jsonl")
    findings.extend(chain_findings)

    for path in TARGETS:
        findings.extend(scan_claims(path, chain_max_n))

    findings.extend(security_scan())

    for finding in findings:
        print(f"[AUDIT] {finding}")

    if args.strict and any(item.startswith("ERROR:") for item in findings):
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
