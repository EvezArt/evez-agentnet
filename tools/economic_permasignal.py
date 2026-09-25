#!/usr/bin/env python3
"""Bridge economic events into EVEZ semantic permasignals."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import semantic_permasignal as ps

TEXT={
 "OPPORTUNITY_DISCOVERED":"economic opportunity observed",
 "OPPORTUNITY_VERIFIED":"economic opportunity verification recorded",
 "BUYER_QUALIFIED":"buyer qualification recorded",
 "OFFER_PROPOSED":"economic offer proposed",
 "OFFER_ACCEPTED":"economic offer accepted and requires human-controlled continuation",
 "DELIVERY_COMMITTED":"delivery commitment recorded and requires human approval",
 "DELIVERABLE_VERIFIED":"deliverable verification recorded",
 "INVOICE_ISSUED":"invoice issued and requires human-controlled continuation",
 "PAYMENT_OBSERVED":"payment observed in economic ledger",
 "RELATIONSHIP_RENEWED":"economic relationship renewal recorded",
 "COST_OBSERVED":"cost observed in economic ledger",
 "MARGIN_COMPUTED":"margin computation recorded",
 "BLOCKED":"economic transition blocked",
 "REJECTED":"economic opportunity rejected",
 "STALE":"economic opportunity marked stale",
 "CONTRADICTED":"economic economic state contradicted"
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",required=True)
    ap.add_argument("--out",default="docs/economy/economic-permasignals.jsonl")
    args=ap.parse_args()
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with out.open("a",encoding="utf-8") as g:
        for line in Path(args.ledger).read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            e=json.loads(line)
            text=TEXT.get(e.get("event_type"),"economic transition recorded")
            if e.get("amount") is not None:
                text += f": {e['currency']} {e['amount']:.2f} ({e.get('amount_semantics','UNKNOWN')})"
            if e.get("state") in {"CONTRADICTED","UNKNOWN","INACCESSIBLE","STALE"}:
                text += f"; epistemic state={e['state']}"
            rec=ps.atom(text,source=f"economic:{e.get('event_id')}",parent=e.get("event_id"))
            mode="REVISE" if e.get("state") in {"CONTRADICTED","STALE","RETRACTED"} else "COMMIT"
            g.write(ps.canon(ps.transition(rec,mode))+"\n")
            count+=1
    print(json.dumps({"source":args.ledger,"output":str(out),"signals_written":count},indent=2))

if __name__=="__main__": main()
