"""Deterministic proof-carrying generation reference core."""
import hashlib, json
from dataclasses import dataclass

EVIDENCE = ("VERIFIED","INFERRED","UNKNOWN","STALE","CONTRADICTED")

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def sha256(x):
    b=x.encode() if isinstance(x,str) else x
    return hashlib.sha256(b).hexdigest()

def event_hash(event):
    return sha256(canonical(event))

def make_event(seed, version, seq, parent, op, payload, evidence="INFERRED"):
    if evidence not in EVIDENCE: raise ValueError("invalid evidence")
    e={"seed":seed,"version":version,"seq":seq,"parent":parent,
       "op":op,"payload":payload,"evidence":evidence}
    e["hash"]=event_hash(e)
    return e

def verify(events):
    parent=""
    for i,e in enumerate(events):
        body=dict(e); actual=body.pop("hash")
        if e["seq"] != i or e["parent"] != parent or event_hash(body) != actual:
            return False
        parent=actual
    return True

def replay(seed, events):
    state={"seed":seed,"items":[]}
    if not verify(events): raise ValueError("invalid spine")
    for e in events:
        if e["op"]=="add": state["items"].append(e["payload"])
        elif e["op"]=="remove" and e["payload"] in state["items"]:
            state["items"].remove(e["payload"])
    return state

def bundle(seed, version, events):
    b={"protocol":"EVEZ-PROOF-1","seed":seed,"version":version,"events":events}
    return {"bundle":b,"checksum":sha256(canonical(b))}

if __name__=="__main__":
    seed="EVEZ-DEMO-001"; version="1"
    events=[]; parent=""
    for i,item in enumerate(("ash","glass","witness")):
        e=make_event(seed,version,i,parent,"add",item)
        events.append(e); parent=e["hash"]
    print(json.dumps({"verified":verify(events),"state":replay(seed,events),
                      "bundle_checksum":bundle(seed,version,events)["checksum"]},sort_keys=True))
