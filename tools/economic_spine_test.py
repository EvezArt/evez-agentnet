#!/usr/bin/env python3
import json,tempfile
from pathlib import Path
import economic_spine

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"economic-events.jsonl"
    a=economic_spine.append_event(p,economic_spine.build_event(
        event_type="OFFER_PROPOSED",state="PROPOSED",amount=1200,currency="USD",
        amount_semantics="PROPOSED",opportunity_id="opp_test",
        source_refs=["obs:test"],evidence_refs=["ev:test"]))
    b=economic_spine.append_event(p,economic_spine.build_event(
        event_type="PAYMENT_OBSERVED",state="OBSERVED",amount=1200,currency="USD",
        amount_semantics="RECEIVED",opportunity_id="opp_test",
        parent_event=a["event_id"],source_refs=["bank:test"],evidence_refs=["receipt:test"]))
    ok,errors=economic_spine.verify(p)
    assert ok, errors
    assert b["previous_event_hash"]==a["event_hash"]
    rows=[json.loads(x) for x in p.read_text().splitlines()]
    assert rows[0]["amount_semantics"]=="PROPOSED"
    assert rows[1]["amount_semantics"]=="RECEIVED"
print("economic spine tests: OK")
