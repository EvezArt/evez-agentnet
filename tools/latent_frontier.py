#!/usr/bin/env python3
"""Create append-only EVEZ negative-space frontier records from audit output.

Every generated frontier retains a stable identity, a source hash, and a
usable evidence reference. Existing journal corruption fails closed.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "docs" / "negative-space.jsonl"

RULES = [
    (re.compile(r"DATE_CONFLICT|chronolog", re.I), "TEMPORAL_GAP", "timeline_reconstructor"),
    (re.compile(r"UNSUPPORTED_COUNT|chain max|623\+", re.I), "REPRODUCTION_GAP", "ledger_reconstructor"),
    (re.compile(r"CONF_1_NON_PRIMARY|confidence", re.I), "SOURCE_GAP", "confidence_calibrator"),
    (re.compile(r"HIGH_RISK_CLAIM|same actor|same infrastructure|OFAC|RICO|admissible", re.I), "MISSING_EVIDENCE", "attribution_verifier"),
    (re.compile(r"SECRET_FILE_TRACKED|SECRET_ARTIFACT|SECRET_CONTENT", re.I), "AUTHORITY_GAP", "credential_boundary_auditor"),
    (re.compile(r"PREV_HASH_MISMATCH|HASH_MISMATCH|DUPLICATE_SEQUENCE|INVALID_JSONL|NON_OBJECT_JSONL|INVALID_RECORD|MISSING_CHAIN", re.I), "REPRODUCTION_GAP", "ledger_integrity_auditor"),
    (re.compile(r"PUBLIC_ARTIFACT_UNMARKED", re.I), "SOURCE_GAP", "public_artifact_manifest"),
]

WHY = {
    "TEMPORAL_GAP":"Chronology constrains causal interpretation.",
    "REPRODUCTION_GAP":"A non-reproducible or structurally invalid record cannot support the weight assigned to it.",
    "SOURCE_GAP":"Provenance and source classification constrain what a claim can establish.",
    "MISSING_EVIDENCE":"Attribution requires direct evidentiary linkage rather than resemblance.",
    "AUTHORITY_GAP":"A secret crossing a repository boundary changes the security model.",
}
FALSIFIER = {
    "TEMPORAL_GAP":"A primary-source timeline resolves the date conflict without contradiction.",
    "REPRODUCTION_GAP":"Independent enumeration or deterministic hash verification reproduces the same chain structure.",
    "SOURCE_GAP":"The missing primary artifact or provenance reference is attached and independently checked.",
    "MISSING_EVIDENCE":"An independent primary artifact directly links the asserted actors, action and time.",
    "AUTHORITY_GAP":"Credentials are rotated or revoked and runtime no longer depends on repository material.",
}
EXPERIMENT = {
    "TEMPORAL_GAP":"Reconstruct a primary-source timeline with normalized timestamps.",
    "REPRODUCTION_GAP":"Enumerate preserved ledger bytes, sequence values, branches and parent hashes.",
    "SOURCE_GAP":"Attach the underlying source object and explicit provenance classification.",
    "MISSING_EVIDENCE":"Identify the smallest direct evidence link and a concrete falsifier.",
    "AUTHORITY_GAP":"Rotate, revoke, scrub current artifacts, then verify secret sourcing.",
}

def stable_id(kind, statement):
    return "ns_" + hashlib.sha256(f"{kind}|{statement}".encode()).hexdigest()[:24]

def finding_id(audit_line):
    return "audit:" + hashlib.sha256(audit_line.encode()).hexdigest()[:32]

def evidence_refs(audit_line):
    refs = [finding_id(audit_line)]
    match = re.search(r"(?P<path>(?:[^:]+/)+[^:]+|(?:docs|forge_output|tools)/[^:]+):(?P<line>\d+):", audit_line)
    if match:
        refs.append(f"{match.group('path')}:{match.group('line')}")
    return refs

def make(kind, statement, source_hash, audit_line):
    return {
        "frontier_id": stable_id(kind, statement),
        "kind": kind,
        "status": "DISCOVERED",
        "statement": statement,
        "why_it_matters": WHY[kind],
        "evidence_refs": evidence_refs(audit_line),
        "dependent_claims": [],
        "falsifier": FALSIFIER[kind],
        "next_experiment": EXPERIMENT[kind],
        "possible_capability": dict((x,y) for _,x,y in RULES)[kind],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parent_frontier_ids": [],
        "source_hash": source_hash,
    }

def load_existing(path):
    existing=set()
    if not path.exists():
        return existing
    raw=path.read_text(encoding="utf-8",errors="replace")
    if raw and not raw.endswith("\n"):
        raise ValueError(f"existing frontier journal has no trailing newline: {path}")
    for line_no,line in enumerate(raw.splitlines(),1):
        if not line.strip(): continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid existing frontier JSON at line {line_no}: {exc}") from exc
        if not isinstance(row,dict) or not row.get("frontier_id"):
            raise ValueError(f"invalid existing frontier record at line {line_no}")
        existing.add(row["frontier_id"])
    return existing

def classify_line(line):
    matches=[]
    for rx,kind,_ in RULES:
        if rx.search(line):
            statement=line.split("[AUDIT] ",1)[-1].strip()
            matches.append((kind,statement))
    return matches

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--audit",required=True)
    ap.add_argument("--out",default=str(DEFAULT_OUT))
    a=ap.parse_args()
    audit_path=Path(a.audit)
    text=audit_path.read_text(encoding="utf-8",errors="replace")
    source_hash=hashlib.sha256(text.encode()).hexdigest()
    records=[]; seen=set()
    for line in text.splitlines():
        if not line.startswith("[AUDIT]"):
            continue
        for kind,statement in classify_line(line):
            rec=make(kind,statement,source_hash,line)
            if rec["frontier_id"] not in seen:
                seen.add(rec["frontier_id"]); records.append(rec)
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    existing=load_existing(out)
    added=0
    with out.open("a",encoding="utf-8") as fh:
        if out.exists() and out.stat().st_size and not out.read_bytes().endswith(b"\n"):
            raise ValueError("refusing to append to frontier journal without newline")
        for rec in records:
            if rec["frontier_id"] in existing: continue
            fh.write(json.dumps(rec,sort_keys=True)+"\n"); added+=1
    print(json.dumps({"discovered":len(records),"appended":added,"source_hash":source_hash},indent=2))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"latent_frontier: {exc}",file=sys.stderr)
        raise SystemExit(2)
