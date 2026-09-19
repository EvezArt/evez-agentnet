#!/usr/bin/env python3
import json,tempfile
from pathlib import Path
import economic_spine

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    ledger=root/"events.jsonl"
    out=root/"signals.jsonl"
    e=economic_spine.append_event(ledger,economic_spine.build_event(
      event_type="PAYMENT_OBSERVED",state="OBSERVED",amount=42,currency="USD",
      amount_semantics="RECEIVED",opportunity_id="opp_signal_test",
      source_refs=["receipt:test"],evidence_refs=["bank:test"]))
    import subprocess,sys
    subprocess.run([sys.executable,"tools/economic_permasignal.py","--ledger",str(ledger),"--out",str(out)],check=True)
    row=json.loads(out.read_text().splitlines()[0])
    assert row["parent_event"]==e["event_id"]
    assert row["mode"]=="COMMIT"
    assert row["state"]=="OBSERVED"
print("economic permasignal bridge: OK")
