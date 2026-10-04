"""Self-test for the EVEZ-OS exposure watchdog.

An audit that cannot be shown to FAIL is worse than no audit (same rule the
repo already states for test_audit_detects.py and test_stack_health.py). So
every path here is exercised for real:

  1. exit 0 on a clean temporary tree
  2. exit 1 when a fake credential is planted -- AND the planted VALUE never
     appears in stdout, stderr, or the evidence file
  3. exit 2 when a check is forced to error, with errored=true in the finding
  4. fingerprint dedup: the same CRITICAL twice notifies once
  5. evidence file lands at evidence/<UTC date>/exposure.jsonl
  6. prose mentioning service_role is NOT a finding (a watchdog that flags its
     own documentation is a watchdog that gets muted)
  7. an ASSIGNED service_role value IS still CRITICAL -- the tightened rule
     must not have disarmed the check it was tightening
  8. placeholder suppression is scoped to prose -- a placeholder-named token in
     an ASSIGNMENT is still CRITICAL, because that is still a credential on
     disk that only rotation can kill

The planted credential is SYNTHETIC and lives only in a temp dir. It is
generated at runtime so no real secret shape is ever committed here -- the
2026-10-02 lesson was that a "real" fixture in this file leaked into a second
repo.

Run: python3 test_exposure_watchdog.py     (exit 1 on any FAIL)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

WATCHDOG = Path(__file__).resolve().parent / "forge_output" / "watchdog.py"
results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


def run_watchdog(roots, env_extra=None, args=()):
    """Invoke the watchdog as a real subprocess so exit codes are real."""
    tmp = Path(tempfile.mkdtemp(prefix="wd-evidence-"))
    env = dict(os.environ)
    env["WATCHDOG_EVIDENCE"] = str(tmp)
    env["WATCHDOG_STATE"] = str(tmp / "state.json")
    # Hermetic probes: a closed loopback port and an unroutable external one,
    # so the gateway verdict does not depend on live network state.
    env["WATCHDOG_LOCAL_HOST"] = "127.0.0.1"
    env["WATCHDOG_LOCAL_PORT"] = "1"          # nothing listens here
    env["WATCHDOG_EXT_HOST"] = "192.0.2.1"    # TEST-NET-1, reserved
    env["WATCHDOG_EXT_PORT"] = "9"
    env["WATCHDOG_PROBE_TIMEOUT"] = "1"
    env.update(env_extra or {})
    cmd = [sys.executable, str(WATCHDOG), "--json", *args]
    for r in roots:
        cmd += ["--root", str(r)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
    return proc, tmp


def evidence_files(tmp):
    return sorted(tmp.rglob("exposure.jsonl"))


# ── 1. clean tree -> exit 0 ────────────────────────────────────────────────
print("1. clean temporary tree must exit 0")
clean = Path(tempfile.mkdtemp(prefix="wd-clean-"))
(clean / "readme.md").write_text("# nothing to see here\nvalue = 42\n")
proc, tmp = run_watchdog([clean])
expect("exit code is 0 on a clean tree", proc.returncode == 0,
       f"rc={proc.returncode} out={proc.stdout[:300]} err={proc.stderr[:300]}")
expect("no CRITICAL reported clean", json.loads(proc.stdout)["critical"] == 0,
       proc.stdout[:200])
expect("summary reports exit_code 0", json.loads(proc.stdout)["exit_code"] == 0)
expect("no check marked errored", json.loads(proc.stdout)["errored_checks"] == [])

# ── 2. planted secret -> exit 1, value never leaks ─────────────────────────
print("\n2. planted fake credential must exit 1 and must NOT echo its value")
# Synthetic, runtime-generated: shape matters, the bytes are meaningless.
FAKE = "clh_" + "SYNTHETICtestonly" + "0" * 20
dirty = Path(tempfile.mkdtemp(prefix="wd-dirty-"))
(dirty / "sub").mkdir()
(dirty / "sub" / "self_interrogation.py").write_text(
    "# synthetic fixture written by test_exposure_watchdog.py\n"
    f'TOKEN = "{FAKE}"\n'
)
proc, tmp2 = run_watchdog([dirty])
combined = proc.stdout + proc.stderr
ev_files = evidence_files(tmp2)
ev_text = "".join(p.read_text() for p in ev_files)
expect("exit code is 1 when a credential is planted", proc.returncode == 1,
       f"rc={proc.returncode} out={proc.stdout[:400]}")
expect("at least one CRITICAL finding", json.loads(proc.stdout)["critical"] >= 1,
       proc.stdout[:200])
expect("SECRET VALUE absent from stdout/stderr", FAKE not in combined,
       "planted value leaked into process output")
expect("SECRET VALUE absent from evidence files", FAKE not in ev_text,
       "planted value leaked into evidence jsonl")
expect("SECRET VALUE absent from state file",
       FAKE not in (tmp2 / "state.json").read_text())
expect("finding names file and line, not value",
       "sub/self_interrogation.py" in ev_text and "clawhub_token" in ev_text)
expect("a line number is reported", ":2" in ev_text or '"lines"' in ev_text)

# ── 3. forced check error -> exit 2 ────────────────────────────────────────
print("\n3. a check that ERRORS must exit 2, never read as clean")
for check in ("gateway", "secrets", "drift"):
    proc, tmp3 = run_watchdog([clean], env_extra={"WATCHDOG_FORCE_ERROR": check})
    expect(f"exit code 2 when {check} errors", proc.returncode == 2,
           f"rc={proc.returncode} out={proc.stdout[:300]}")
    ev = "".join(p.read_text() for p in evidence_files(tmp3))
    expect(f"{check} error produced a WARN finding",
           '"severity": "WARN"' in ev and f'"{check}"' in ev)
    expect(f"{check} error marked errored=true", '"errored": true' in ev)
    expect(f"{check} error did NOT report clean",
           json.loads(proc.stdout)["critical"] >= 0 and
           json.loads(proc.stdout)["errored_checks"] == [check],
           proc.stdout[:200])

# ── 4. fingerprint dedup ───────────────────────────────────────────────────
print("\n4. same CRITICAL twice must notify only once")
proc_a, tmp4 = run_watchdog([dirty])
first = json.loads(proc_a.stdout)
proc_b, _ = run_watchdog([dirty], env_extra={})  # separate state -> fresh again
# Same state dir this time, to actually exercise the seen-set.
env_state = str(tmp4 / "state.json")
proc_c, _ = run_watchdog([dirty], env_extra={"WATCHDOG_STATE": env_state})
second = json.loads(proc_c.stdout)
expect("first run sees the new CRITICAL", first["new_critical"] >= 1, str(first))
expect("second run dedups by fingerprint -> 0 new",
       second["new_critical"] == 0, str(second))
expect("fingerprints are identical across runs",
       set(first["fingerprints"]) & set(second["fingerprints"]) != set())
seen = json.loads(Path(env_state).read_text())["seen"]
expect("seen-set keyed by fingerprint", all(len(k) == 16 for k in seen), str(list(seen)[:3]))
# Same planted tree twice -> identical fingerprint set, proving the fingerprint
# is derived from stable identity and not from the timestamp.
expect("identical fingerprint set across identical runs",
       sorted(first["fingerprints"]) == sorted(second["fingerprints"]),
       f"{sorted(first['fingerprints'])} != {sorted(second['fingerprints'])}")

# ── 5. evidence file shape ─────────────────────────────────────────────────
print("\n5. evidence lands in a date-named subdirectory as exposure.jsonl")
today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
expect("evidence dir is named for today's UTC date",
       (tmp2 / today / "exposure.jsonl").exists(),
       f"expected {tmp2 / today / 'exposure.jsonl'}")
rows = [json.loads(l) for l in
        (tmp2 / today / "exposure.jsonl").read_text().strip().splitlines() if l.strip()]
expect("every row has a severity",
       all(r.get("severity") in ("CRITICAL", "WARN", "INFO") for r in rows))
expect("every row has a fingerprint", all(len(r.get("fingerprint", "")) == 16 for r in rows))
expect("every row has check + where", all(r.get("check") and r.get("where") for r in rows))
expect("rows are valid JSONL append records", len(rows) >= 1)

# ── 6. prose is not a secret ───────────────────────────────────────────────
# The first real run reported 6 of 11 CRITICALs that were the WORD
# "service_role" in audit prose, a grep one-liner, and the watchdog's own
# pattern table. A watchdog that flags its own documentation trains Steven to
# ignore the channel, so the rule must require an assignment to a value.
print("\n6. prose mentioning service_role must NOT be a CRITICAL")
prose = Path(tempfile.mkdtemp(prefix="wd-prose-"))
(prose / "audit.md").write_text(
    "FINDING 1 - HIGH: Supabase `service_role` key in public repo\n")
(prose / "grepper.py").write_text(
    'subprocess.run(["grep", "-rl", "service_role", "/root"])\n')
proc, _ = run_watchdog([prose])
rows = [json.loads(l) for l in
        evidence_files(_)[0].read_text().strip().splitlines() if l.strip()]
prose_hits = [r for r in rows if r["check"] == "secrets" and r["severity"] == "CRITICAL"]
expect("prose-only tree reports no CRITICAL secrets finding", not prose_hits,
       f"{[r['where'] for r in prose_hits]}")
expect("prose-only tree exits 0", proc.returncode == 0, f"rc={proc.returncode}")

# ── 7. the tightened rule still catches a real assignment ─────────────────
print("\n7. an assigned service_role value is still CRITICAL")
real = Path(tempfile.mkdtemp(prefix="wd-assigned-"))
(real / "cfg.ts").write_text('const service_role = "abcdefghij0123456789ABCDEF"\n')
proc, tmp7 = run_watchdog([real])
rows = [json.loads(l) for l in
        (tmp7 / today / "exposure.jsonl").read_text().strip().splitlines() if l.strip()]
hits = [r for r in rows if r["check"] == "secrets" and r["severity"] == "CRITICAL"]
expect("assigned service_role value is CRITICAL", hits, "no CRITICAL emitted")
expect("finding names the file", any("cfg.ts" in r["where"] for r in hits),
       f"{[r['where'] for r in hits]}")
expect("assigned-value tree exits 1", proc.returncode == 1, f"rc={proc.returncode}")

# ── 8. placeholder suppression is scoped to PROSE, never to a value ───────
# A first cut suppressed any line containing a placeholder, which silently
# disarmed the planted-credential test above: its synthetic token contains
# "testonly" inside a real assignment. Suppression must apply to comments and
# docs only. A placeholder-named token in an assignment is still the only copy
# of a credential-shaped string on disk.
print("\n8. placeholder suppression applies to prose, not to assigned values")
fix = Path(tempfile.mkdtemp(prefix="wd-fixture-"))
(fix / "test_fixture.py").write_text(
    "# a documented placeholder, never a real value: clh_0000TESTONLY00000000\n"
    'token = "clh_0000TESTONLYnotreal0000zzzzZZZZffffFFFF"\n')
proc, tmp8 = run_watchdog([fix])
rows = [json.loads(l) for l in
        (tmp8 / today / "exposure.jsonl").read_text().strip().splitlines() if l.strip()]
hits = [r for r in rows if r["check"] == "secrets" and r["severity"] == "CRITICAL"]
expect("prose comment with a placeholder is suppressed", len(hits) == 1,
       f"expected exactly the assigned value, got {[r['where'] for r in hits]}")
expect("the assigned placeholder-named token is still CRITICAL",
       any("test_fixture.py:2" in r["where"] for r in hits),
       f"{[r['where'] for r in hits]}")
expect("assigned-value tree exits 1", proc.returncode == 1, f"rc={proc.returncode}")

# ── summary ────────────────────────────────────────────────────────────────
failed = [n for n, ok in results if not ok]
print("\n{}/{} checks passed".format(len(results) - len(failed), len(results)))
if failed:
    print("FAILED:")
    for n in failed:
        print("  - " + n)
    sys.exit(1)
print("exposure watchdog self-test OK")
sys.exit(0)
