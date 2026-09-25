#!/usr/bin/env python3
"""Reduce the economic event stream to a factual acquisition state.

No ranking is treated as truth and no proposed/contracted/invoiced amount is
reported as received cash.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--ledger",required=True); args=ap.parse_args()
    rows=[]
    for line in Path(args.ledger).read_text(encoding="utf-8").splitlines():
        if line.strip(): rows.append(json.loads(line))
    byopp={}
    for e in rows:
        oid=e.get("opportunity_id") or "UNASSIGNED"
        byopp.setdefault(oid,[]).append(e)
    state=[]
    for oid,events in byopp.items():
        last=events[-1]
        amounts={}
        for sem in ["PROPOSED","CONTRACTED","INVOICED","RECEIVED","COST"]:
            vals={}
            for e in events:
                if e.get("amount_semantics")==sem and isinstance(e.get("amount"),(int,float)):
                    c=e.get("currency","USD"); vals[c]=round(vals.get(c,0)+float(e["amount"]),2)
            if vals: amounts[sem]=vals
        state.append({
          "opportunity_id":oid,
          "latest_event_type":last.get("event_type"),
          "latest_epistemic_state":last.get("state"),
          "amounts":amounts,
          "evidence_refs":sorted({r for e in events for r in e.get("evidence_refs",[])}),
          "provenance_refs":sorted({r for e in events for r in e.get("provenance_refs",[])}),
          "external_action_allowed":False,
          "next_mode":"REVIEW" if last.get("state") in {"CONTRADICTED","UNKNOWN","INACCESSIBLE","STALE"} else "EXECUTE_WITH_APPROVAL"
        })
    totals={}
    for s in state:
        for sem,vals in s["amounts"].items():
            for c,a in vals.items(): totals.setdefault(sem,{})[c]=round(totals.setdefault(sem,{}).get(c,0)+a,2)
    print(json.dumps({"opportunities":state,"totals_by_semantics":totals,"cash_definition":"RECEIVED events only","truth_policy":"proposals, contracts, invoices, and cash remain distinct"},indent=2))
if __name__=="__main__": main()
