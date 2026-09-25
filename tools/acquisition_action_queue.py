#!/usr/bin/env python3
"""Generate a bounded acquisition action queue from verified opportunities.

This tool only prepares actions. It never contacts a buyer, submits an
application, signs an agreement, invoices, or moves money.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path

def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--queue",required=True)
    ap.add_argument("--out",default="docs/economy/acquisition-actions.jsonl")
    ap.add_argument("--min-budget",type=float,default=250)
    args=ap.parse_args()
    rows=[]
    for line in Path(args.queue).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as f:
        for row in rows:
            budget=row.get("budget")
            action="DRAFT_PROPOSAL" if budget is None or budget >= args.min_budget else "REQUEST_APPROVAL"
            rec={
                "schema":"EVEZ-ACQUISITION-ACTION/1",
                "action_id":"act_"+digest({"opportunity_id":row["opportunity_id"],"action":action})[:20],
                "opportunity_id":row["opportunity_id"],
                "action":action,
                "state":"DRAFT",
                "human_approval_required":True,
                "external_action_allowed":False,
                "approved_by":None,"approved_at":None,"executed_at":None,
                "evidence_refs":row.get("evidence_refs",[]),
                "notes":"Prepared only. Re-verify source status before any human-approved external action."
            }
            f.write(json.dumps(rec,sort_keys=True,separators=(",",":"))+"\n")
    print(json.dumps({"output":str(out),"records":len(rows),"external_action_allowed":False,"human_approval_required":True},indent=2))

if __name__=="__main__":
    main()
