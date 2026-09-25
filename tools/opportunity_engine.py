#!/usr/bin/env python3
"""Evidence-backed opportunity normalizer.

Input: JSONL observations already obtained through an authorized/public surface.
Output: JSONL acquisition queue. No outreach, transactions, authentication bypass,
or fabricated budget/revenue occurs here.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def words(s): return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{1,}",s.lower())}
def as_list(v):
    if v is None:return []
    return [str(x) for x in v] if isinstance(v,list) else [str(v)]
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()

def build(row,caps):
    title=str(row.get("title","")).strip()
    need=str(row.get("need","")).strip()
    text=f"{title} {need}"
    nw=words(text); cw=words(" ".join(caps))
    matched=sorted(nw & cw)
    evidence=as_list(row.get("evidence_refs"))
    basis=[]
    score=0
    if evidence: score+=25; basis.append("evidence references present")
    else: basis.append("evidence references missing")
    if matched:
        score+=min(55,10+9*len(matched))
        basis.append("capability terms overlap: "+", ".join(matched[:12]))
    else: basis.append("no capability-term overlap established")
    if row.get("budget") is not None: score+=10; basis.append("budget explicitly observed")
    else: basis.append("budget unknown")
    if row.get("deadline"): score+=10; basis.append("deadline explicitly observed")
    else: basis.append("deadline unknown")
    score=min(score,100)
    oid="opp_"+digest({"source":row.get("source",{}),"title":title,"need":need})[:20]
    verified=bool(row.get("source",{}).get("uri") and evidence)
    state="VERIFIED" if verified else "DISCOVERED"
    if score>=60 and matched: state="QUALIFIED"
    return {
      "schema":"EVEZ-OPPORTUNITY/1","opportunity_id":oid,"state":state,
      "source":{
        "uri":str(row.get("source",{}).get("uri","")),
        "observed_at":str(row.get("source",{}).get("observed_at",now())),
        "content_hash":row.get("source",{}).get("content_hash"),
        "observation_ref":row.get("source",{}).get("observation_ref")
      },
      "title":title or "Untitled observed opportunity",
      "buyer_ref":row.get("buyer_ref"),
      "need":need or "Need not yet established",
      "deadline":row.get("deadline"),"budget":row.get("budget"),
      "currency":row.get("currency"),
      "evidence_refs":evidence,"capability_refs":caps,
      "capability_fit":matched,"fit_score":score,"fit_basis":basis,
      "next_test":("Verify buyer identity, scope, deadline, and budget from the source." if not verified
                   else "Verify that the observed need is still open and that the referenced capability satisfies the stated scope."),
      "next_action":"Prepare an offer draft; do not send without explicit human approval.",
      "contact_boundary":"HUMAN_APPROVAL_REQUIRED","human_approval_required":True,
      "content_hash":None
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True); ap.add_argument("--output",default="docs/economy/opportunities.jsonl")
    ap.add_argument("--capability",action="append",required=True)
    args=ap.parse_args()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with open(args.input,encoding="utf-8") as f, out.open("a",encoding="utf-8") as g:
        for line in f:
            if not line.strip(): continue
            row=json.loads(line); item=build(row,args.capability)
            payload=dict(item); payload["content_hash"]=digest(payload)
            g.write(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n"); count+=1
    print(json.dumps({"input":args.input,"output":str(out),"records_written":count},indent=2))
if __name__=="__main__": main()
