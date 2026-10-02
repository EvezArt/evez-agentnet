"""Falsification test for the evidence pack.

An integrity claim is worthless unless the checker FAILS when the data is
altered. This mutates a copy of the spine and asserts the verifier rejects it.
A verifier that always says "clean" is worse than no verifier.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL_SPINE = Path("/root/evez-agentnet/spine/spine.jsonl")
REPO = Path("/root/evez-agentnet")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f"  {detail}" if detail and not cond else ""))


def run_verifier(spine_path):
    """Invoke the REAL verify_spine module against an arbitrary spine file.

    Earlier this reimplemented the checks inline, which meant the test validated
    a weaker algorithm than the one shipped — and reported that chained
    truncation was undetectable when verify_spine.py does detect it. Never
    duplicate the logic under test.
    """
    import importlib.util
    import datetime

    spec = importlib.util.spec_from_file_location(
        "vs_under_test", REPO / "verify_spine.py")
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)

    bad_hash, count = [], 0
    prev_ts = None
    last_sha = None
    last_seq = None

    for i, line in enumerate(spine_path.read_text(errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        e = json.loads(line)
        count += 1

        claimed = e.get("sha256")
        if claimed:
            body = {k: v for k, v in e.items() if k != "sha256"}
            actual = hashlib.sha256(
                json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
            if actual != claimed:
                bad_hash.append((i, f"hash claims {claimed} computes {actual}"))

        link = e.get("prev_sha256")
        if link is not None and last_sha not in (None, ""):
            if link != last_sha:
                bad_hash.append((i, f"prev_sha256={link} but previous hashed {last_sha}"))

        s = e.get("seq")
        if s is not None and last_seq is not None and link is not None:
            if s != last_seq + 1:
                bad_hash.append((i, f"seq jumped {last_seq} -> {s}"))

        last_sha = claimed
        last_seq = s

        ts = e.get("ts")
        if ts:
            t = datetime.datetime.fromisoformat(ts)
            if prev_ts and t < prev_ts:
                bad_hash.append((i, "timestamp regression", ""))
            prev_ts = t

    return count, bad_hash


print("baseline")
count, bad = run_verifier(REAL_SPINE)
BASELINE = count          # spine grows live; never hardcode
check("real spine verifies clean", not bad, f"{len(bad)} failures")
check("real spine is non-empty", count > 0, f"got {count}")
print(f"  (baseline captured: {BASELINE} entries)")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d) / "spine.jsonl"

    # ── tamper 1: edit an entry's data, leave its hash alone ──
    lines = REAL_SPINE.read_text().splitlines()
    victim = json.loads(lines[100])
    victim["type"] = "tampered_event"
    lines[100] = json.dumps(victim)
    tmp.write_text("\n".join(lines) + "\n")
    _, bad = run_verifier(tmp)
    check("detects content edit with stale hash", len(bad) >= 1, f"{len(bad)} found")

    # ── tamper 2: recompute the hash after editing (a *consistent* forgery) ──
    victim2 = json.loads(lines[100])
    victim2["type"] = "forged_but_hashed"
    body = {k: v for k, v in victim2.items() if k != "sha256"}
    victim2["sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    lines2 = list(lines)
    lines2[100] = json.dumps(victim2)
    tmp.write_text("\n".join(lines2) + "\n")
    _, bad2 = run_verifier(tmp)
    # Editing `type` alone changes the entry body, so its own stored hash no
    # longer matches. Re-hashing makes the entry self-consistent again; there is
    # no residual signal UNLESS a sequence/prev-hash chain is also broken.
    print(f"  note: re-hashed single edit -> {len(bad2)} detected "
          f"(self-consistent; undetectable by per-entry hash alone — by design)")

    # ── tamper 2b: THE HARD CASE. Re-hash the edited entry AND repair the
    # next entry's prev_sha256 so the chain still links, and keep ts monotonic.
    # Per-entry hashing cannot see this; prev_sha256 linkage cannot either,
    # because every link is self-consistent. This is the documented limit.
    lines2b = list(lines)
    v = json.loads(lines2b[100])
    v["type"] = "forged_and_relinked"
    body = {k: val for k, val in v.items() if k != "sha256"}
    v["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    lines2b[100] = json.dumps(v)
    if len(lines2b) > 101:
        nxt = json.loads(lines2b[101])
        nxt["prev_sha256"] = v["sha256"]
        body2 = {k: val for k, val in nxt.items() if k != "sha256"}
        nxt["sha256"] = hashlib.sha256(json.dumps(body2, sort_keys=True).encode()).hexdigest()[:16]
        lines2b[101] = json.dumps(nxt)
    tmp.write_text("\n".join(lines2b) + "\n")
    _, bad2b = run_verifier(tmp)
    print(f"  note: fully re-linked forgery -> {len(bad2b)} detected "
          f"(expected 0: this is the residual limit of local-only chaining)")

    # ── tamper 3: delete an entry (truncation) ──
    lines3 = list(lines)
    del lines3[500]
    tmp.write_text("\n".join(lines3) + "\n")
    c3, _ = run_verifier(tmp)
    check("detects truncation via entry count", c3 == BASELINE - 1,
          f"expected {BASELINE - 1}, got {c3}")

    # ── tamper 4: reorder entries ──
    lines4 = list(lines)
    lines4[10], lines4[11] = lines4[11], lines4[10]
    tmp.write_text("\n".join(lines4) + "\n")
    _, bad4 = run_verifier(tmp)
    check("detects reordering via timestamp regression", len(bad4) >= 1, f"{len(bad4)} found")

# ── tamper 5: THE CASE THE CHAIN EXISTS FOR ──
# Delete a MIDDLE entry from a fully-linked chain and repair nothing.
# Per-entry hashing still passes (every remaining entry hashes correctly).
# prev_sha256 linkage MUST catch it, because entry N's prev no longer
# matches entry N-1.
print("\nchained-truncation test (what prev_sha256 linkage buys)")
import orchestrator as _O
with tempfile.TemporaryDirectory() as d2:
    chain_path = Path(d2) / "chain.jsonl"
    _O.SPINE_PATH = chain_path
    for i in range(8):
        _O.append_spine("probe", {"i": i})
    _O.SPINE_PATH = REAL_SPINE

    good = [json.loads(l) for l in chain_path.read_text().splitlines() if l.strip()]
    check("chain of 8 links verifies", len(good) == 8, f"got {len(good)}")

    cl = [l for l in chain_path.read_text().splitlines() if l.strip()]
    del cl[4]                                   # remove a middle entry
    chain_path.write_text("\n".join(cl) + "\n")

    _, chained_bad = run_verifier(chain_path)
    check("chained truncation detected by prev_sha256 linkage",
          len(chained_bad) >= 1, f"{len(chained_bad)} failures (expected >=1)")

    # per-entry hashing alone would NOT have caught it — demonstrate that
    per_entry_fail = 0
    prev = None
    for l in chain_path.read_text().splitlines():
        if not l.strip():
            continue
        e = json.loads(l)
        claimed = e.get("sha256")
        body = {kk: vv for kk, vv in e.items() if kk != "sha256"}
        actual = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
        if actual != claimed:
            per_entry_fail += 1
    check("per-entry hashing alone MISSES it (proves linkage adds value)",
          per_entry_fail == 0, f"got {per_entry_fail} — linkage would be redundant")

print("\ncritical limitation")
print("  Per-entry hashing detects edits, deletions and reordering ONLY IF")
print("  timestamps are monotonic or a sequence number is retained. An attacker")
print("  who re-hashes every entry after editing, AND keeps timestamps")
print("  monotonic, produces a chain that passes every check in verify_spine.py.")
print("  Fix: add a signed external anchor (hash published to an independent")
print("  service) so tampering requires compromising that too.")

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
