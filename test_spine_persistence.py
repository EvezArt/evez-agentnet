#!/usr/bin/env python3
"""Regression tests for the :9116 Event Spine.

Defects these cover, each found by execution on the live service:
  1. The spine kept every event in memory, so a restart silently discarded the
     chain while /verify still reported `valid: true` over an empty sequence.
  2. `/verify` returned valid=True for an empty chain - a vacuous pass.
  3. The ledger had no write path, so nothing was ever persisted.

These load the REAL module. Do not reimplement the hashing here: a
hand-copied checker validates a weaker algorithm than the one shipped.
"""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

SPINE = Path("/root/offspring/evez-cub-1/workspace/skills/evez-firmament/services/event_spine.py")
if not SPINE.exists():
    alt = Path("/root/evez-firmament/services/event_spine.py")
    if alt.exists():
        SPINE = alt


def load_spine(ledger_path, token="test-token-abc123"):
    """Import event_spine fresh with an isolated ledger and a known token."""
    os.environ["EVEZ_SPINE_TOKEN"] = token
    os.environ["EVEZ_SPINE_LEDGER"] = str(ledger_path)
    spec = importlib.util.spec_from_file_location("spine_under_test", SPINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if not SPINE.exists():
        print("SKIP: event_spine.py not present on this host "
              f"(looked in {SPINE}). Persistence cannot be asserted here.")
        return 0
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"  PASS {name}")
        else:
            print(f"  FAIL {name} {detail}")
            failures.append(name)

    print("== 1. fail-closed: no token means the module refuses to import ==")
    saved = os.environ.get("EVEZ_SPINE_TOKEN")
    os.environ["EVEZ_SPINE_LEDGER"] = str(Path(tempfile.mkdtemp()) / "x.jsonl")
    os.environ["EVEZ_SPINE_TOKEN"] = ""
    spec = importlib.util.spec_from_file_location("spine_notoken", SPINE)
    m2 = importlib.util.module_from_spec(spec)
    refused = False
    try:
        spec.loader.exec_module(m2)
    except SystemExit:
        refused = True
    check("empty token refused at import", refused)
    if saved is not None:
        os.environ["EVEZ_SPINE_TOKEN"] = saved

    print("== 2. events survive a restart (persistence) ==")
    tmp = Path(tempfile.mkdtemp())
    ledger = tmp / "spine.jsonl"
    a = load_spine(ledger)
    for i in range(4):
        a.SPINE.append("persistence", f"act-{i}", {"i": i})
    head_before = a.SPINE.verify()["head_hash"]
    count_before = a.SPINE.verify()["events_checked"]

    b = load_spine(ledger)  # simulates a process restart
    v = b.SPINE.verify()
    check("chain count preserved across restart",
          v.get("events_checked") == count_before,
          f"{v.get('events_checked')} != {count_before}")
    check("head hash identical across restart",
          v.get("head_hash") == head_before,
          f"{v.get('head_hash')} != {head_before}")
    check("ledger file actually exists on disk", ledger.exists())
    check("verify reports persisted=true", v.get("persisted") is True)
    check("restarted chain verifies valid", v["valid"] is True, str(v["errors"]))

    print("== 3. tampering is detected ==")
    lines = [json.loads(x) for x in ledger.read_text().splitlines() if x.strip()]
    lines[1]["data"] = {"i": "TAMPERED"}
    ledger.write_text(chr(10).join(json.dumps(x) for x in lines) + chr(10))
    c = load_spine(ledger)
    v2 = c.SPINE.verify()
    check("edited payload fails verification", v2["valid"] is False)
    check("tamper names the offending seq",
          any(e.get("seq") == 1 for e in v2["errors"]), str(v2["errors"])[:200])

    print("== 4. empty chain is not a vacuous pass ==")
    d = load_spine(tmp / "empty.jsonl")
    v3 = d.SPINE.verify()
    check("empty chain reports valid=False", v3["valid"] is False, str(v3))
    check("empty chain explains itself",
          any("empty" in str(e.get("error", "")) for e in v3["errors"]))

    print("== 5. genesis link and seq numbering ==")
    e = load_spine(tmp / "fresh2.jsonl")
    ev = e.SPINE.append("d", "a", {})
    check("first event prev_hash is genesis", ev["prev_hash"] == "0" * 64)
    check("first event seq is 0", ev["seq"] == 0)
    ev2 = e.SPINE.append("d", "b", {})
    check("second event seq is 1", ev2["seq"] == 1)
    check("second event links to first hash", ev2["prev_hash"] == ev["hash"])

    print()
    if failures:
        print(f"FAILED: {len(failures)} -> {failures}")
        return 1
    print("all spine persistence checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
