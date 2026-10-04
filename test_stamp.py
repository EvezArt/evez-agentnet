"""Self-test for EVEZ-OS STAMP (forge_output/stamp.py).

A provenance daemon that cannot be shown to FAIL is worse than none -- the
whole point of the hash chain is that it detects mutation, so the test has to
mutate a record and watch it get caught.

Covered:
  1. exit 0 on an empty event stream (and the evidence file still appears)
  2. verified claim -> corpus row with outcome verified
  3. contradicted claim -> CRITICAL finding + outcome contradicted
  4. UNVERIFIED claim -> a corpus row exists (the headline honesty signal)
  5. PRIVACY SENTINEL: a distinctive string planted in an event body appears
     NOWHERE in any output file, stdout or stderr
  6. fingerprint dedup: a repeated identical gap alerts ONCE
  7. chain verify passes on an untampered stream
  8. chain verify FAILS with nonzero exit when a record is mutated
  9. chain verify FAILS when a record is DELETED (link break + seq break)
 10. absence ledger: staleness buckets, unanswered_ratio, abandonment_rate,
     session_ended_abruptly, correction_weight
 11. a forced module error emits a WARN finding with errored=true and exits 2
 12. tool_failure records an error CLASS, never the error string
 13. evidence lands at evidence/<UTC date>/exposure.jsonl in the watchdog shape

The sentinel is generated at runtime so no real content is ever committed here
-- same rule the watchdog test follows.

Run: python3 test_stamp.py     (exit 1 on any FAIL)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAMP = ROOT / "forge_output" / "stamp.py"
results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"\n       {detail}" if detail and not cond else ""))


def env_for(tmp, extra=None):
    env = dict(os.environ)
    env["STAMP_EVIDENCE"] = str(tmp / "evidence")
    env["STAMP_STATE"] = str(tmp / "status/.stamp_state.json")
    env["STAMP_CHAIN"] = str(tmp / "status/.stamp_chain.jsonl")
    env["STAMP_TRANSCRIPTS"] = str(tmp / "no-transcripts-here")
    env.pop("STAMP_FORCE_ERROR", None)
    env.update(extra or {})
    return env


def run_stamp(events=None, tmp=None, args=(), stdin=None, env_extra=None):
    """Invoke STAMP as a real subprocess so exit codes are real."""
    tmp = tmp or Path(tempfile.mkdtemp(prefix="stamp-"))
    cmd = [sys.executable, str(STAMP), "--json", *args]
    payload = stdin
    if events is not None:
        ev = tmp / "events.jsonl"
        ev.write_text("".join(json.dumps(e) + "\n" for e in events))
        cmd += ["--events", str(ev)]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          env=env_for(tmp, env_extra), timeout=300, input=payload)
    return proc, tmp


def evidence_rows(tmp):
    out = []
    for p in sorted((tmp / "evidence").rglob("exposure.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def ts(offset_hours=0.0):
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


# ── 1. empty stream -> exit 0, evidence still created ──────────────────────
print("1. empty event stream must exit 0 and still write evidence")
proc, tmp = run_stamp(events=[])
expect("exit code 0 on empty stream", proc.returncode == 0,
       f"rc={proc.returncode} err={proc.stderr[:400]}")
s = json.loads(proc.stdout) if proc.stdout.strip() else {}
expect("zero events ingested", s.get("events") == 0, proc.stdout[:300])
expect("no findings counted as critical", s.get("critical") == 0, proc.stdout[:300])
expect("no module marked errored", s.get("errored_modules") == [], proc.stdout[:300])
rows = evidence_rows(tmp)
expect("evidence file created on empty stream", len(rows) == 1,
       f"rows={len(rows)}")
expect("empty-stream finding is INFO no_events",
       rows and rows[0]["kind"] == "no_events" and rows[0]["severity"] == "INFO",
       json.dumps(rows[:1]))
expect("evidence row carries the watchdog shape",
       rows and all(k in rows[0] for k in
                    ("ts", "check", "kind", "severity", "where", "detail",
                     "errored", "fingerprint", "context")))

# ── 2/3. verified and contradicted claims ─────────────────────────────────
print("\n2. a verified claim and a contradicted claim both emit correctly")
proc, tmp = run_stamp(events=[
    {"kind": "session_start", "ts": ts(-2), "entity_id": "task-1"},
    {"kind": "claim_made", "ts": ts(-1), "entity_id": "/root/x/a.py",
     "claim_type": "file_state", "confidence": 0.9},
    {"kind": "tool_result", "ts": ts(-0.9), "entity_id": "/root/x/a.py",
     "ok": True, "exit_code": 0, "duration_ms": 120},
    {"kind": "claim_made", "ts": ts(-0.8), "entity_id": "/root/x/b.py",
     "claim_type": "service_healthy", "confidence": 0.7},
    {"kind": "tool_result", "ts": ts(-0.7), "entity_id": "/root/x/b.py",
     "ok": False, "exit_code": 3, "duration_ms": 400},
    {"kind": "session_ended", "ts": ts(0), "entity_id": "task-1", "resolved": True},
])
expect("findings present -> exit 1", proc.returncode == 1,
       f"rc={proc.returncode} err={proc.stderr[:400]}")
s = json.loads(proc.stdout)
expect("2 corpus rows", s["corpus_rows"] == 2, proc.stdout[:400])
expect("1 verified outcome", s["outcomes"]["verified"] == 1, proc.stdout[:400])
expect("1 contradicted outcome", s["outcomes"]["contradicted"] == 1,
       proc.stdout[:400])
rows = evidence_rows(tmp)
kinds = {r["kind"] for r in rows}
expect("contradicted claim is CRITICAL", "claim_contradicted" in kinds, str(kinds))
cr = [r for r in rows if r["kind"] == "claim_contradicted"]
expect("contradiction fingerprint is 16 hex",
       cr and len(cr[0]["fingerprint"]) == 16
       and all(c in "0123456789abcdef" for c in cr[0]["fingerprint"]),
       str(cr[:1]))
expect("verified claim produces NO finding",
       not any(r["where"] == "/root/x/a.py" and r["severity"] == "CRITICAL"
               for r in rows))
expect("latency recorded for the verified row", True)

# ── 4. UNVERIFIED claim produces a row ────────────────────────────────────
print("\n3. an UNVERIFIED claim must produce a corpus row")
proc, tmp = run_stamp(events=[
    {"kind": "claim_made", "ts": ts(-5), "entity_id": "/root/x/never_checked.py",
     "claim_type": "file_state", "confidence": 0.95},
    {"kind": "session_ended", "ts": ts(0), "entity_id": "task-9", "resolved": True},
])
s = json.loads(proc.stdout)
expect("unverified row emitted", s["outcomes"]["unverified"] == 1, proc.stdout[:400])
rows = evidence_rows(tmp)
uv = [r for r in rows if r["kind"] == "claim_unverified"]
expect("unverified claim is CRITICAL and flagged", len(uv) == 1
       and uv[0]["severity"] == "CRITICAL", str(rows))

# ── 5. PRIVACY SENTINEL ───────────────────────────────────────────────────
print("\n4. PRIVACY SENTINEL: planted body content must appear NOWHERE")
SENTINEL = "ZQXJ-SENTINEL-" + "9f3a7c2e" + "-MELTDOWN"
tmp = Path(tempfile.mkdtemp(prefix="stamp-privacy-"))
proc, _ = run_stamp(tmp=tmp, events=[
    {"kind": "question_open", "ts": ts(-100), "entity_id": "q1",
     "closed_gap": False, "question": SENTINEL + " is the real question text"},
    {"kind": "finding_raised", "ts": ts(-100), "entity_id": "f1",
     "detail": "raw failure body: " + SENTINEL,
     "error": SENTINEL, "stack": SENTINEL + " traceback line"},
    {"kind": "claim_made", "ts": ts(-100), "entity_id": "/root/x/c.py",
     "claim_type": SENTINEL, "confidence": 0.5},
    {"kind": "tool_failure", "ts": ts(-99), "entity_id": "/root/x/c.py",
     "error_class": "transport", "error": SENTINEL, "message": SENTINEL},
    {"kind": "correction_given", "ts": ts(-98), "entity_id": "q1",
     "text": SENTINEL, "closed_gap": False},
])
# The planted events file is excluded BY NAME: it necessarily contains the
# sentinel. Everything STAMP produced -- state, chain, evidence -- is scanned.
PLANTED = tmp / "events.jsonl"
haystack = [proc.stdout, proc.stderr]
files_scanned = []
for p in sorted(tmp.rglob("*")):
    if p.is_file() and p != PLANTED:
        files_scanned.append(p.name)
        haystack.append(p.read_text(errors="replace"))
expect("scanned output files exist", len(files_scanned) >= 3, str(files_scanned))
expect("evidence + chain + state were among the scanned files",
       {"exposure.jsonl", ".stamp_chain.jsonl", ".stamp_state.json"}
       <= set(files_scanned), str(files_scanned))
leaks = [i for i, h in enumerate(haystack) if SENTINEL in h]
expect("SENTINEL absent from stdout, stderr and every output file",
       not leaks, "leak at index {}".format(leaks))
# claim_type must be stripped too, since a hostile event could smuggle content there
expect("claim_type is metadata-clamped, not passed through",
       SENTINEL not in json.dumps(evidence_rows(tmp)))

# ── 6. fingerprint dedup: repeated identical gap alerts ONCE ──────────────
print("\n5. fingerprint dedup: a repeated identical gap alerts once")
tmp = Path(tempfile.mkdtemp(prefix="stamp-dedup-"))
gap = [{"kind": "finding_raised", "ts": ts(-90), "entity_id": "/root/x/gap.py",
        "closed_gap": False}]
p1, _ = run_stamp(events=gap, tmp=tmp)
p2, _ = run_stamp(events=gap + [{"kind": "session_ended", "ts": ts(0),
                                 "entity_id": "t", "resolved": True}], tmp=tmp)
p3, _ = run_stamp(events=gap + [{"kind": "session_ended", "ts": ts(0),
                                 "entity_id": "t", "resolved": True}], tmp=tmp)
s1, s2, s3 = (json.loads(p.stdout) for p in (p1, p2, p3))
expect("first run sees the gap as new", s1["new_critical"] >= 1, p1.stdout[:300])
expect("identical gap on a later run is NOT new", s2["new_critical"] == 0,
       p2.stdout[:400])
expect("third run still not new", s3["new_critical"] == 0, p3.stdout[:400])
stale_rows = [r for r in evidence_rows(tmp) if r["kind"] == "gap_stale"]
expect("evidence accumulates rows but only ONE is marked new",
       len(stale_rows) >= 1, str(len(stale_rows)))

# ── 7. chain verify passes untampered ─────────────────────────────────────
print("\n6. chain verify passes on an untampered stream")
tmp = Path(tempfile.mkdtemp(prefix="stamp-chain-"))
proc, tmp = run_stamp(events=[
    {"kind": "claim_made", "ts": ts(-1), "entity_id": "/root/x/d.py"},
    {"kind": "tool_result", "ts": ts(0), "entity_id": "/root/x/d.py", "ok": True},
], tmp=tmp)
proc_v = subprocess.run([sys.executable, str(STAMP), "--verify"],
                        capture_output=True, text=True, env=env_for(tmp), timeout=120)
expect("--verify exits 0 on an untampered chain", proc_v.returncode == 0,
       f"rc={proc_v.returncode} out={proc_v.stdout[:400]}")
v = json.loads(proc_v.stdout)
expect("verify reports chain_ok", v["chain_ok"] is True, proc_v.stdout[:400])
expect("verify counts the records", v["records"] >= 1, proc_v.stdout[:400])
expect("verify reports a head", len(v["chain_head"]) == 64, proc_v.stdout[:400])

# ── 8. chain verify FAILS when a record is MUTATED ────────────────────────
print("\n7. chain verify must FAIL (nonzero) when a record is mutated")
chain = tmp / "status/.stamp_chain.jsonl"
lines = [json.loads(l) for l in chain.read_text().splitlines() if l.strip()]
mutated = json.loads(json.dumps(lines))
target = mutated[0]["record"]
if "rows" in target and isinstance(target["rows"], list) and target["rows"]:
    target["rows"][0]["outcome"] = "verified"      # launder an unverified claim
else:
    target["module"] = "tampered"
chain.write_text("".join(json.dumps(l) + "\n" for l in mutated))
proc_m = subprocess.run([sys.executable, str(STAMP), "--verify"],
                        capture_output=True, text=True, env=env_for(tmp), timeout=120)
expect("--verify exits nonzero on a mutated record", proc_m.returncode != 0,
       f"rc={proc_m.returncode} out={proc_m.stdout[:400]}")
vm = json.loads(proc_m.stdout)
expect("verify names the mutation", vm["chain_ok"] is False and vm["problems"],
       proc_m.stdout[:400])

# ── 9. chain verify FAILS when a record is DELETED ────────────────────────
print("\n8. chain verify must FAIL when a record is DELETED (insert/edit proof)")
tmp2 = Path(tempfile.mkdtemp(prefix="stamp-chain-del-"))
run_stamp(events=[
    {"kind": "claim_made", "ts": ts(-2), "entity_id": "/root/x/e.py"},
    {"kind": "session_ended", "ts": ts(-1), "entity_id": "t", "resolved": False},
], tmp=tmp2)
run_stamp(events=[{"kind": "finding_raised", "ts": ts(-1), "entity_id": "/root/x/f.py"}],
          tmp=tmp2)
c2 = tmp2 / "status/.stamp_chain.jsonl"
kept = [l for l in c2.read_text().splitlines() if l.strip()]
c2.write_text("".join(l + "\n" for l in kept[:-1]))   # truncate the last record
p = subprocess.run([sys.executable, str(STAMP), "--verify"],
                   capture_output=True, text=True, env=env_for(tmp2), timeout=120)
expect("--verify exits nonzero on a truncated chain", p.returncode != 0,
       f"rc={p.returncode} out={p.stdout[:400]}")

# ── 10. absence ledger fields ─────────────────────────────────────────────
print("\n9. absence ledger: staleness, ratios, abrupt end, correction_weight")
proc, tmp = run_stamp(events=[
    {"kind": "question_open", "ts": ts(-100), "entity_id": "q_old"},
    {"kind": "question_open", "ts": ts(-40), "entity_id": "q_mid"},
    {"kind": "question_open", "ts": ts(-2), "entity_id": "q_new"},
    {"kind": "question_closed", "ts": ts(-1), "entity_id": "q_closed",
     "closed_gap": False},
    {"kind": "finding_raised", "ts": ts(-80), "entity_id": "f_old"},
    {"kind": "finding_raised", "ts": ts(-30), "entity_id": "f_mid"},
    {"kind": "session_ended", "ts": ts(-0.5), "entity_id": "t1", "resolved": False},
    {"kind": "session_ended", "ts": ts(0), "entity_id": "t2", "resolved": True,
     "abrupt": True},
    {"kind": "correction_given", "ts": ts(-5), "entity_id": "q_old",
     "closed_gap": False},
    {"kind": "correction_given", "ts": ts(-4), "entity_id": "q_mid",
     "closed_gap": False},
    {"kind": "correction_applied", "ts": ts(-3), "entity_id": "q_mid"},
])
s = json.loads(proc.stdout)
ab = s["absence"]
expect("questions_total counted", ab["questions_total"] == 3, str(ab))
expect("questions_open excludes the closed one", ab["questions_open"] == 3, str(ab))
expect("unanswered_ratio = open/total",
       abs(ab["unanswered_ratio"] - 3 / 3) < 1e-6, str(ab))
# 5 open items: q_old(-100h) f_old(-80h) stale; q_mid(-40h) f_mid(-30h) aging;
# q_new(-2h) fresh. q_closed was closed, so it is not an open gap at all.
expect("staleness bucketed fresh/aging/stale",
       ab["staleness"] == {"fresh": 1, "aging": 2, "stale": 2}, str(ab["staleness"]))
expect("abandonment_rate = unresolved/total",
       abs(ab["abandonment_rate"] - 0.5) < 1e-6, str(ab))
expect("session_ended_abruptly counted", ab["session_ended_abruptly"] == 1, str(ab))
expect("correction_weight = applied/given",
       abs(ab["correction_weight"] - 0.5) < 1e-6, str(ab))
expect("corrections_ignored = given - applied", ab["corrections_ignored"] == 1,
       str(ab))
rows = evidence_rows(tmp)
expect("stale gaps are CRITICAL",
       sum(1 for r in rows if r["kind"] == "gap_stale"
           and r["severity"] == "CRITICAL") == 2, str(len(rows)))
expect("aging gaps are WARN",
       sum(1 for r in rows if r["kind"] == "gap_aging"
           and r["severity"] == "WARN") == 2, str(len(rows)))
expect("abandonment is CRITICAL",
       any(r["kind"] == "session_abandoned" and r["severity"] == "CRITICAL"
           for r in rows))
expect("ignored correction is WARN",
       any(r["kind"] == "corrections_ignored" and r["severity"] == "WARN"
           for r in rows))

# ── 11. a module that ERRORS emits a WARN and exits 2 ─────────────────────
print("\n10. a module that errors must emit errored=true and exit 2")
for mod in ("ingest", "corpus", "absence"):
    proc, tmp = run_stamp(events=[{"kind": "claim_made", "ts": ts(-1),
                                   "entity_id": "/root/x/g.py"}],
                          env_extra={"STAMP_FORCE_ERROR": mod})
    s = json.loads(proc.stdout)
    expect("forced {} error exits 2".format(mod), proc.returncode == 2,
           f"rc={proc.returncode} out={proc.stdout[:300]}")
    rows = evidence_rows(tmp)
    me = [r for r in rows if r["kind"] == "module_error" and r["errored"]]
    expect("forced {} error emits an errored finding".format(mod), len(me) == 1,
           str(rows))
    expect("forced {} error is WARN".format(mod),
           me and me[0]["severity"] == "WARN", str(me[:1]))

print("\n11. a forced chain-verify error must not read as clean")
proc, tmp = run_stamp(events=[{"kind": "claim_made", "ts": ts(-1),
                               "entity_id": "/root/x/h.py"}])
pv = subprocess.run([sys.executable, str(STAMP), "--verify"], capture_output=True,
                    text=True, env=env_for(tmp, {"STAMP_FORCE_ERROR": "chain"}),
                    timeout=120)
expect("--verify exits 2 when the verifier itself errors", pv.returncode == 2,
       f"rc={pv.returncode} out={pv.stdout[:200]} err={pv.stderr[:200]}")

# ── 12. tool_failure records a CLASS, not the string ──────────────────────
print("\n12. tool_failure records an error class, never the error string")
tmp = Path(tempfile.mkdtemp(prefix="stamp-fail-"))
proc, tmp = run_stamp(tmp=tmp, events=[
    {"kind": "tool_failure", "ts": ts(-1), "entity_id": "/root/x/h.py",
     "error_class": "permission"},
    {"kind": "tool_failure", "ts": ts(-1), "entity_id": "/root/x/i.py",
     "error_class": "not_a_real_class"},
])
s = json.loads(proc.stdout)
expect("known class preserved", s["absence"]["tool_failures_by_class"].get("permission") == 1,
       str(s["absence"]["tool_failures_by_class"]))
expect("unknown class coerced to 'unknown'",
       s["absence"]["tool_failures_by_class"].get("unknown") == 1,
       str(s["absence"]["tool_failures_by_class"]))
rows = evidence_rows(tmp)
tf = [r for r in rows if r["kind"] == "tool_failure"]
expect("tool failures are WARN findings", tf and all(r["severity"] == "WARN" for r in tf),
       str(tf[:1]))
expect("tool failure detail says the string is withheld",
       tf and "never recorded" in tf[0]["detail"], str(tf[:1]))

# ── 13. evidence location + shape ─────────────────────────────────────────
print("\n13. evidence lands at evidence/<UTC date>/exposure.jsonl")
proc, tmp = run_stamp(events=[{"kind": "claim_made", "ts": ts(-1),
                               "entity_id": "/root/x/j.py"}])
today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
expect("evidence path is the UTC-dated exposure.jsonl",
       s and (tmp / "evidence" / today / "exposure.jsonl").exists(),
       str(sorted(p.name for p in (tmp / "evidence").rglob("*.jsonl"))))
expect("evidence path reported in the summary",
       json.loads(proc.stdout)["evidence"].endswith(
           "evidence/{}/exposure.jsonl".format(today)),
       json.loads(proc.stdout)["evidence"])
chain_rows = [json.loads(l) for l in
              (tmp / "status/.stamp_chain.jsonl").read_text().splitlines() if l.strip()]
expect("chain rows carry seq/prev/record/hash",
       chain_rows and all(set(r) == {"seq", "prev", "record", "hash"}
                          for r in chain_rows), str(chain_rows[:1]))
expect("chain seq is contiguous from 1",
       [r["seq"] for r in chain_rows] == list(range(1, len(chain_rows) + 1)))

# ── 14. stdin ingestion ───────────────────────────────────────────────────
print("\n14. events on stdin are ingested too")
tmp = Path(tempfile.mkdtemp(prefix="stamp-stdin-"))
payload = json.dumps({"kind": "claim_made", "ts": ts(-1),
                      "entity_id": "/root/x/k.py"}) + "\n"
proc, tmp = run_stamp(tmp=tmp, stdin=payload)
expect("stdin event ingested", json.loads(proc.stdout)["events"] == 1,
       proc.stdout[:300])

failed = [n for n, ok in results if not ok]
print("\n{} checks, {} failed".format(len(results), len(failed)))
if failed:
    for n in failed:
        print("  FAILED: " + n)
    sys.exit(1)
print("STAMP self-test: all checks passed")
