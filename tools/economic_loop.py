#!/usr/bin/env python3
"""EVEZ economic acquisition loop.

One bounded command:
  observations -> opportunity records -> economic events -> human-state signals

It never sends outreach, signs contracts, invoices, moves money, or bypasses
authorization. All externally consequential actions remain explicit human gates.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--observations",required=True)
    ap.add_argument("--capability",action="append",required=True)
    ap.add_argument("--opportunities",default="docs/economy/opportunities.jsonl")
    ap.add_argument("--ledger",default="docs/economy/economic-events.jsonl")
    ap.add_argument("--signals",default="docs/economy/economic-permasignals.jsonl")
    args=ap.parse_args()

    run([sys.executable,str(TOOLS/"opportunity_engine.py"),
         "--input",args.observations,"--output",args.opportunities,
         *sum((["--capability",c] for c in args.capability),[])])

    # Every discovered/normalized opportunity receives an economic event.
    opportunities=[]
    p=Path(args.opportunities)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip(): opportunities.append(json.loads(line))

    spine=TOOLS/"economic_spine.py"
    for o in opportunities:
        event_type="OPPORTUNITY_VERIFIED" if o["state"] in {"VERIFIED","QUALIFIED"} else "OPPORTUNITY_DISCOVERED"
        state="SUPPORTED" if event_type=="OPPORTUNITY_VERIFIED" else "OBSERVED"
        run([sys.executable,str(spine),"--ledger",args.ledger,"add",
             "--type",event_type,"--state",state,
             "--opportunity-id",o["opportunity_id"],
             "--need",o["need"],
             *sum((["--evidence",x] for x in o.get("evidence_refs",[])),[]),
             *sum((["--source",x] for x in [o.get("source",{}).get("uri","")] if x),[]),
             "--notes",o["next_test"]])

    run([sys.executable,str(TOOLS/"economic_permasignal.py"),
         "--ledger",args.ledger,"--out",args.signals])
    print(json.dumps({
        "observations":args.observations,
        "opportunities_output":args.opportunities,
        "economic_ledger":args.ledger,
        "permasignal_output":args.signals,
        "external_action_allowed":False,
        "human_approval_required":True
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
