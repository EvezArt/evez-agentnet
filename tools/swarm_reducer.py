#!/usr/bin/env python3
"""Deterministic reducer for many semantic signals.

Input: JSONL permasignals.
Output: one compact human-state packet plus durable frontier items.
No majority-vote truth engine. Conflicts survive reduction.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def h(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def reduce_rows(rows):
    states=Counter(r.get("state","UNKNOWN") for r in rows)
    contradictions=[r for r in rows if r.get("state")=="CONTRADICTED"]
    unknowns=[r for r in rows if r.get("state") in ("UNKNOWN","INACCESSIBLE")]
    proposals=[r for r in rows if r.get("state")=="PROPOSED"]
    observed=[r for r in rows if r.get("state") in ("OBSERVED","SUPPORTED")]
    packet={
      "grammar":"EVEZ-HSM/1","kind":"human_state_packet",
      "state":"CONTRADICTED" if contradictions else ("UNKNOWN" if unknowns and not observed else "SUPPORTED" if observed else "UNKNOWN"),
      "counts":dict(states),
      "observations":[r.get("text") for r in observed[-12:]],
      "uncertainties":[r.get("text") for r in unknowns[-12:]],
      "proposals":[r.get("text") for r in proposals[-8:]],
      "conflicts":[r.get("text") for r in contradictions[-12:]],
      "next_mode":"REVISE" if contradictions else "TEST" if unknowns else "COMMIT",
    }
    packet["packet_hash"]=h(packet)
    return packet

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("path")
    a=ap.parse_args()
    rows=[]
    with open(a.path,encoding="utf-8") as f:
      for line in f:
        if line.strip(): rows.append(json.loads(line))
    print(json.dumps(reduce_rows(rows),ensure_ascii=False,separators=(",",":")))

if __name__=="__main__": main()
