#!/usr/bin/env python3
import json, tempfile, os
from semantic_permasignal import atom, transition, append

def main():
    a=atom("observed response hash returned","test")
    assert a["state"]=="OBSERVED"
    b=transition(a,"DISTINGUISH")
    assert b["mode"]=="DISTINGUISH"
    with tempfile.TemporaryDirectory() as d:
        p=os.path.join(d,"x.jsonl")
        r1=append(p,b); r2=append(p,transition(atom("unknown surface","test"),"ORIENT"))
        assert r1["previous_event_hash"] is None
        assert r2["previous_event_hash"]==r1["event_hash"]
        assert len(r2["event_hash"])==64
    print("semantic_permasignal: PASS")
if __name__=="__main__": main()
