#!/usr/bin/env python3
"""Semantic PermaSignal: error-reducing human-state machine for EVEZ.

Turns observations, boundaries, contradictions, and proposed actions into
canonical, append-only communication atoms. It never upgrades uncertainty
into fact and never authorizes an action by itself.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone

STATES = ("OBSERVED","SUPPORTED","INFERRED","PROPOSED","UNKNOWN","INACCESSIBLE","CONTRADICTED","STALE","RETRACTED")
MODES = ("RECEIVE","ORIENT","DISTINGUISH","TEST","COMMIT","REVISE","HANDOFF")
SEVERITY = ("info","attention","blocker")

def now(): return datetime.now(timezone.utc).isoformat()
def canon(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))
def digest(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def classify(text: str):
    t=text.lower()
    if re.search(r"\b(error|failed|failure|exception|contradict|broken|invalid)\b",t): return "CONTRADICTED","blocker"
    if re.search(r"\b(missing|unknown|unclear|inaccessible|unavailable|cannot|can't)\b",t): return "UNKNOWN","attention"
    if re.search(r"\b(propose|proposal|should|could|maybe|might|possible)\b",t): return "PROPOSED","attention"
    if re.search(r"\b(observed|measured|recorded|returned|status|hash)\b",t): return "OBSERVED","info"
    return "UNKNOWN","attention"

def atom(text, source="human", parent=None):
    state, severity=classify(text)
    rec={"grammar":"EVEZ-HSM/1","kind":"permasignal","state":state,
         "severity":severity,"mode":"ORIENT","source":source,"text":text,
         "observed_at":now(),"parent_event":parent}
    rec["content_hash"]=digest(rec)
    return rec

def transition(rec, mode):
    if mode not in MODES: raise ValueError(mode)
    out=dict(rec); out["mode"]=mode; out["transition_hash"]=digest(out)
    return out

def append(path, rec):
    prev=None
    try:
        with open(path,encoding="utf-8") as f:
            for line in f:
                if line.strip(): prev=json.loads(line).get("event_hash")
    except FileNotFoundError: pass
    rec=dict(rec); rec["previous_event_hash"]=prev
    rec["event_hash"]=digest(rec)
    with open(path,"a",encoding="utf-8") as f: f.write(canon(rec)+"\n")
    return rec

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--source",default="human")
    ap.add_argument("--mode",choices=MODES,default="ORIENT")
    ap.add_argument("--out",default="docs/permasignal.jsonl")
    a=ap.parse_args()
    print(json.dumps(append(a.out,transition(atom(a.text,a.source),a.mode)),ensure_ascii=False,separators=(",",":")))

if __name__=="__main__": main()
