#!/usr/bin/env python3
"""Audit EVEZ forensic material for provenance, chronology, security and overclaiming."""
from __future__ import annotations
import argparse,json,re,subprocess
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HIGH_RISK=re.compile(r"(?:\b(?:confirmed|proved|proven|same actor|same syndicate|same infrastructure|not coincidence|cover.?up|criminal enterprise|RICO|OFAC violation|legally admissible|admissible|criminal charges warranted)\b|99\.1%|100%|623\+|62 million|fixed payouts|188 citations)",re.I)
HISTORICAL_MARKER="EVEZ CLAIM STATUS: HISTORICAL_DRAFT"

def tracked_files():
    try:
        out=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT,text=False)
    except (OSError,subprocess.CalledProcessError):
        return []
    return [ROOT/x for x in out.decode(errors="replace").split("\0") if x]

def parse_iso(value):
    try: datetime.fromisoformat(str(value).replace("Z","+00:00")); return True
    except Exception: return False

def canonical_hash(record):
    body=dict(record); body.pop("h",None)
    import hashlib
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def audit_chain(path):
    findings=[]; records=[]
    if not path.exists(): return [f"ERROR:MISSING_CHAIN:{path}"],None
    raw_lines=path.read_text(encoding="utf-8",errors="replace").splitlines()
    if not raw_lines: return [f"ERROR:EMPTY_CHAIN:{path}"],None
    for line_no,raw in enumerate(raw_lines,1):
        if not raw.strip(): findings.append(f"ERROR:BLANK_CHAIN_LINE:{path}:{line_no}"); continue
        try: record=json.loads(raw)
        except json.JSONDecodeError:
            findings.append(f"ERROR:INVALID_JSONL:{path}:{line_no}"); continue
        if not isinstance(record,dict):
            findings.append(f"ERROR:NON_OBJECT_JSONL:{path}:{line_no}"); continue
        required={"n","t","k","d","h","ph"}
        missing=sorted(required-set(record))
        if missing: findings.append(f"ERROR:INVALID_RECORD:{path}:{line_no}:missing={missing}")
        if not isinstance(record.get("n"),int) or isinstance(record.get("n"),bool): findings.append(f"ERROR:INVALID_SEQUENCE:{path}:{line_no}")
        if not isinstance(record.get("t"),str) or not parse_iso(record.get("t")): findings.append(f"ERROR:INVALID_TIMESTAMP:{path}:{line_no}")
        if not isinstance(record.get("k"),str) or not record.get("k"): findings.append(f"ERROR:INVALID_KIND:{path}:{line_no}")
        if not isinstance(record.get("d"),dict): findings.append(f"ERROR:INVALID_PAYLOAD:{path}:{line_no}")
        if not isinstance(record.get("h"),str) or not re.fullmatch(r"[0-9a-f]{64}",str(record.get("h"))): findings.append(f"ERROR:INVALID_HASH:{path}:{line_no}")
        if not isinstance(record.get("ph"),str) or not re.fullmatch(r"[0-9a-f]{64}",str(record.get("ph"))): findings.append(f"ERROR:INVALID_PREV_HASH:{path}:{line_no}")
        if all(x in record for x in ("n","t","k","d","h","ph")) and isinstance(record.get("d"),dict):
            if canonical_hash(record)!=record.get("h"): findings.append(f"ERROR:HASH_MISMATCH:{path}:{line_no}")
        records.append(record)
    if not records: return findings+[f"ERROR:EMPTY_VALID_CHAIN:{path}"],None
    seqs=[r.get("n") for r in records if isinstance(r.get("n"),int) and not isinstance(r.get("n"),bool)]
    if len(seqs)!=len(records): findings.append(f"ERROR:UNSEQUENCED_RECORDS:{path}")
    if seqs:
        findings.append(f"INFO:CHAIN_RECORDS:{len(records)}"); findings.append(f"INFO:CHAIN_MAX_N:{max(seqs)}")
        if seqs!=sorted(seqs): findings.append("WARN:NON_MONOTONIC_SEQUENCE:n values are not ordered ascending; require an explicit branch_id if intentional")
        dupes=sorted({n for n in seqs if seqs.count(n)>1})
        if dupes: findings.append(f"ERROR:DUPLICATE_SEQUENCE:{dupes}")
    for i,rec in enumerate(records):
        if i==0: continue
        if rec.get("ph") != records[i-1].get("h"): findings.append(f"ERROR:PREV_HASH_MISMATCH:{path}:record_index={i}")
    conf1=[r for r in records if isinstance(r.get("d"),dict) and r["d"].get("conf")==1.0 and r["d"].get("source") not in (None,"PRIMARY_RECORD")]
    if conf1: findings.append(f"WARN:CONF_1_NON_PRIMARY:{len(conf1)} records")
    return findings,max(seqs) if seqs else None

def scan_claims(path,chain_max):
    try: text=path.read_text(encoding="utf-8",errors="replace")
    except OSError: return [f"ERROR:MISSING_OR_UNREADABLE:{path}"]
    lines=text.splitlines()
    header=lines[:8]
    historical=any(line.lstrip().startswith(f"<!-- {HISTORICAL_MARKER}") or HISTORICAL_MARKER in line for line in header)
    hits=[]
    risk_lines=[]
    for line_no,line in enumerate(lines,1):
        if HIGH_RISK.search(line): risk_lines.append(f"WARN:HIGH_RISK_CLAIM:{path}:{line_no}:{line.strip()[:240]}")
    if not historical:
        hits.extend(risk_lines)
        if path.suffix.lower() in {".md",".html"} and risk_lines:
            hits.append(f"WARN:PUBLIC_ARTIFACT_UNMARKED:{path}:high-risk public artifact lacks a header marker")
    if "June 10, 2019" in text and "May 24, 2026" in text:
        hits.append(f"WARN:DATE_CONFLICT:{path}:contains both the 2019 WYDOT incident date and a 2026 incident label")
    if "623+" in text and (chain_max is None or chain_max<623):
        hits.append(f"WARN:UNSUPPORTED_COUNT:{path}:contains 623+ while current public chain max is {chain_max}")
    return hits

SECRET_ASSIGN=re.compile(r"(?im)\b(?:API[_-]?KEY|TOKEN|PASSWORD|SECRET|PAT|AUTH(?:ORIZATION)?)[A-Z0-9_ -]*[:=]\s*(?!\$\{|REDACTED|<REDACTED>|YOUR_|changeme)["']?[A-Za-z0-9_./+=:-]{16,}["']?")

def security_scan():
    findings=[]
    tracked=tracked_files()
    env_pattern=re.compile(r"(^|/)\.env(?:\.|$)|(?:\.pem|\.p12|\.pfx)$|(^|/)(?:id_rsa|id_ed25519)(?:$|\.)",re.I)
    for path in tracked:
        rel=path.relative_to(ROOT)
        rel_text=str(rel)
        documented_example = ".example." in rel_text or rel_text.endswith(".example.env") or rel_text.startswith("docs/examples/")
        if env_pattern.search(rel_text) and not documented_example:
            findings.append(f"ERROR:SECRET_FILE_TRACKED:{rel}")
        if path.suffix.lower() in {".png",".jpg",".jpeg",".gif",".zip",".pdf",".woff",".woff2"}: continue
        try: text=path.read_text(encoding="utf-8",errors="replace")
        except OSError: continue
        for m in SECRET_ASSIGN.finditer(text):
            if "CREDENTIAL_ROTATION_REQUIRED.md" in str(rel) and "VULTR_API_KEY" in m.group(0): continue
            findings.append(f"ERROR:SECRET_CONTENT:{rel}:{m.start()}")
            break
    return findings

def target_files():
    files=[]
    for base in (ROOT/"docs",ROOT/"forge_output"):
        if not base.exists(): continue
        files.extend(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in {".md",".html"})
    return sorted(set(files))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--strict",action="store_true")
    args=parser.parse_args(); findings=[]; chain,chain_max=audit_chain(ROOT/"docs"/"permaaudit-chain.jsonl"); findings.extend(chain)
    for path in target_files(): findings.extend(scan_claims(path,chain_max))
    findings.extend(security_scan())
    for f in findings: print("[AUDIT] "+f)
    return 2 if args.strict and any(x.startswith("ERROR:") for x in findings) else 0

if __name__=="__main__": raise SystemExit(main())
