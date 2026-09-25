#!/usr/bin/env python3
"""Append-only EVEZ economic ledger.

The ledger records economic facts and state transitions without conflating
opportunity, proposal, contract, invoice, or observed payment.
"""

from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA="EVEZ-ECON/1"
STATES={"OBSERVED","SUPPORTED","INFERRED","PROPOSED","UNKNOWN","INACCESSIBLE","CONTRADICTED","STALE","RETRACTED"}
SEMS={"UNKNOWN","PROPOSED","CONTRACTED","INVOICED","RECEIVED","COST"}

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def h_bytes(b): return hashlib.sha256(b).hexdigest()

def content_hash(e):
    x=dict(e); x.pop("content_hash",None); x.pop("event_hash",None)
    return h_bytes(canonical(x))

def chain_hash(e, previous):
    x=dict(e); x["previous_event_hash"]=previous; x.pop("event_hash",None)
    return h_bytes(canonical(x))

def build_event(**kw):
    state=kw["state"]; sem=kw.get("amount_semantics","UNKNOWN"); amount=kw.get("amount")
    if state not in STATES: raise ValueError(f"invalid state: {state}")
    if sem not in SEMS: raise ValueError(f"invalid amount_semantics: {sem}")
    if amount is not None and amount < 0: raise ValueError("amount must be >= 0")
    event_type=kw["event_type"]
    human=event_type in {"OFFER_ACCEPTED","DELIVERY_COMMITTED","INVOICE_ISSUED","RELATIONSHIP_RENEWED"}
    return {
        "schema":SCHEMA,
        "event_id":h_bytes(f"{event_type}|{now()}|{os.urandom(16).hex()}".encode())[:20],
        "event_type":event_type,
        "occurred_at":now(),
        "state":state,
        "opportunity_id":kw.get("opportunity_id"),
        "buyer_ref":kw.get("buyer_ref"),
        "need":kw.get("need"),
        "capability_refs":kw.get("capability_refs") or [],
        "currency":kw.get("currency","USD").upper(),
        "amount":amount,
        "amount_semantics":sem,
        "source_refs":kw.get("source_refs") or [],
        "provenance_refs":kw.get("provenance_refs") or [],
        "evidence_refs":kw.get("evidence_refs") or [],
        "parent_event":kw.get("parent_event"),
        "previous_event_hash":None,
        "human_approval_required":human,
        "external_action_allowed":False,
        "notes":kw.get("notes")
    }

def append_event(path,event):
    path.parent.mkdir(parents=True,exist_ok=True)
    previous=None
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row=json.loads(line); previous=row.get("event_hash")
    event["previous_event_hash"]=previous
    event["content_hash"]=content_hash(event)
    event["event_hash"]=chain_hash(event,previous)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,sort_keys=True,separators=(",",":"))+"\n")
    return event

def verify(path):
    errors=[]; previous=None
    if not path.exists(): return True,errors
    for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except Exception as e: errors.append(f"line {n}: invalid JSON: {e}"); continue
        if row.get("previous_event_hash")!=previous: errors.append(f"line {n}: previous_event_hash mismatch")
        if row.get("content_hash")!=content_hash(row): errors.append(f"line {n}: content_hash mismatch")
        if row.get("event_hash")!=chain_hash(row,previous): errors.append(f"line {n}: event_hash mismatch")
        previous=row.get("event_hash")
    return not errors,errors

def money_state(path):
    buckets={"RECEIVED":{},"CONTRACTED":{},"INVOICED":{},"COST":{}}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            e=json.loads(line); amt=e.get("amount"); sem=e.get("amount_semantics"); cur=e.get("currency","USD")
            if isinstance(amt,(int,float)) and sem in buckets:
                buckets[sem][cur]=round(buckets[sem].get(cur,0.0)+float(amt),2)
    return {"observed_received":buckets["RECEIVED"],"contracted":buckets["CONTRACTED"],"invoiced":buckets["INVOICED"],"observed_costs":buckets["COST"]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ledger",default="docs/economy/economic-events.jsonl")
    sp=ap.add_subparsers(dest="cmd",required=True)
    a=sp.add_parser("add"); a.add_argument("--type",required=True); a.add_argument("--state",required=True)
    a.add_argument("--amount",type=float); a.add_argument("--currency",default="USD"); a.add_argument("--semantics",default="UNKNOWN")
    a.add_argument("--opportunity-id"); a.add_argument("--buyer-ref"); a.add_argument("--need")
    for n in ["capability","source","provenance","evidence"]: a.add_argument("--"+n,action="append",default=[])
    a.add_argument("--parent-event"); a.add_argument("--notes")
    sp.add_parser("verify"); sp.add_parser("money")
    args=ap.parse_args(); path=Path(args.ledger)
    if args.cmd=="verify":
        ok,errors=verify(path); print(json.dumps({"ok":ok,"ledger":str(path),"errors":errors},indent=2)); return 0 if ok else 2
    if args.cmd=="money":
        print(json.dumps(money_state(path),indent=2)); return 0
    e=build_event(event_type=args.type,state=args.state,amount=args.amount,currency=args.currency,amount_semantics=args.semantics,
                  opportunity_id=args.opportunity_id,buyer_ref=args.buyer_ref,need=args.need,capability_refs=args.capability,
                  source_refs=args.source,provenance_refs=args.provenance,evidence_refs=args.evidence,parent_event=args.parent_event,notes=args.notes)
    print(json.dumps(append_event(path,e),indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
