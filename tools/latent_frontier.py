#!/usr/bin/env python3
"""Create append-only EVEZ negative-space frontier records from audit output."""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parents[1] / 'docs' / 'negative-space.jsonl'

RULES = [
    (re.compile(r'DATE_CONFLICT|chronolog', re.I), 'TEMPORAL_GAP', 'timeline_reconstructor'),
    (re.compile(r'UNSUPPORTED_COUNT|chain max|623\\+', re.I), 'REPRODUCTION_GAP', 'ledger_reconstructor'),
    (re.compile(r'CONF_1_NON_PRIMARY|confidence', re.I), 'SOURCE_GAP', 'confidence_calibrator'),
    (re.compile(r'HIGH_RISK_CLAIM|same actor|same infrastructure|OFAC|RICO|admissible', re.I), 'MISSING_EVIDENCE', 'attribution_verifier'),
    (re.compile(r'SECRET_FILE_TRACKED|SECRET_ARTIFACT', re.I), 'AUTHORITY_GAP', 'credential_boundary_auditor'),
]

WHY = {
    'TEMPORAL_GAP':'Chronology constrains causal interpretation.',
    'REPRODUCTION_GAP':'A non-reproducible count cannot support the weight assigned to it.',
    'SOURCE_GAP':'Confidence requires a defined estimator and independent calibration.',
    'MISSING_EVIDENCE':'Attribution requires direct evidentiary linkage rather than resemblance.',
    'AUTHORITY_GAP':'A secret crossing a repository boundary changes the security model.',
}
FALSIFIER = {
    'TEMPORAL_GAP':'A primary-source timeline resolves the date conflict without contradiction.',
    'REPRODUCTION_GAP':'Independent enumeration reproduces the same sequence and count.',
    'SOURCE_GAP':'A predeclared calibration and out-of-sample test supports the estimator.',
    'MISSING_EVIDENCE':'An independent primary artifact directly links the asserted actors, action and time.',
    'AUTHORITY_GAP':'Credentials are rotated or revoked and runtime no longer depends on repository material.',
}
EXPERIMENT = {
    'TEMPORAL_GAP':'Reconstruct a primary-source timeline with normalized timestamps.',
    'REPRODUCTION_GAP':'Enumerate preserved chain bytes, sequence values, branches and parent hashes.',
    'SOURCE_GAP':'Attach estimator definition, ground truth, calibration and independent evaluation.',
    'MISSING_EVIDENCE':'Identify the smallest direct evidence link and a concrete falsifier.',
    'AUTHORITY_GAP':'Rotate, revoke, scrub current artifacts, then verify secret sourcing.',
}

def sid(kind, statement, source_hash):
    return 'ns_' + hashlib.sha256(f'{kind}|{statement}|{source_hash}'.encode()).hexdigest()[:24]

def make(kind, statement, source_hash):
    return {
        'frontier_id': sid(kind, statement, source_hash),
        'kind': kind, 'status':'DISCOVERED', 'statement':statement,
        'why_it_matters':WHY[kind], 'evidence_refs':['forensic_claim_audit'],
        'dependent_claims':[], 'falsifier':FALSIFIER[kind],
        'next_experiment':EXPERIMENT[kind], 'possible_capability':dict((x,y) for _,x,y in RULES)[kind],
        'created_at':datetime.now(timezone.utc).isoformat(), 'parent_frontier_ids':[],
        'source_hash':source_hash,
    }

def main():
    p=argparse.ArgumentParser(); p.add_argument('--audit', required=True); p.add_argument('--out', default=str(DEFAULT_OUT)); a=p.parse_args()
    text=Path(a.audit).read_text(encoding='utf-8', errors='replace')
    source_hash=hashlib.sha256(text.encode()).hexdigest()
    records=[]; seen=set()
    for line in text.splitlines():
        if not line.startswith('[AUDIT]'): continue
        for rx,kind,_ in RULES:
            if rx.search(line):
                stmt=line.split(':',2)[-1].strip(); rec=make(kind,stmt,source_hash)
                if rec['frontier_id'] not in seen: seen.add(rec['frontier_id']); records.append(rec)
                break
    out=Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    existing=set()
    if out.exists():
        for line in out.read_text(encoding='utf-8').splitlines():
            try: existing.add(json.loads(line).get('frontier_id'))
            except json.JSONDecodeError: pass
    added=0
    with out.open('a',encoding='utf-8') as fh:
        for rec in records:
            if rec['frontier_id'] in existing: continue
            fh.write(json.dumps(rec, sort_keys=True)+'\n'); added+=1
    print(json.dumps({'discovered':len(records),'appended':added,'source_hash':source_hash},indent=2))

if __name__ == '__main__': main()