#!/usr/bin/env python3
import json
from pathlib import Path

def main():
    p=Path(__file__).resolve().parents[1]/"docs/economy/acquisition-queue-2026-09-19.jsonl"
    rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    assert rows
    ids=[r["opportunity_id"] for r in rows]
    assert len(ids)==len(set(ids)), "duplicate opportunity ids"
    for r in rows:
        assert r["human_approval_required"] is True
        assert r["contact_boundary"]=="HUMAN_APPROVAL_REQUIRED"
        assert r["source"]["uri"].startswith(("http://","https://"))
        if r["budget"] is not None: assert r["budget"] >= 0
    print("acquisition queue invariants: PASS")
if __name__=="__main__":
    main()
