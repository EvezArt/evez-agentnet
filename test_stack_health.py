"""Falsification test for stack_health.py.

A health check that cannot fail is worse than none — it manufactures
confidence. This deliberately breaks conditions and asserts each is caught.

Nothing here mutates production state: it calls the module's check()
directly with known-bad inputs.
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sh_under_test", "/root/evez-agentnet/stack_health.py")
SH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SH)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("detector behaviour")

# hard failure
SH.FAIL.clear()
SH.check("svc", False, "down")
expect("hard failure routes to FAIL", len(SH.FAIL) == 1, f"{SH.FAIL}")

# warning-only — must clear BOTH lists; FAIL still holds the prior entry
SH.FAIL.clear(); SH.WARN.clear()
SH.check("yield", False, "cosmetic", warn_only=True)
expect("warn_only routes to WARN, not FAIL",
       len(SH.WARN) == 1 and len(SH.FAIL) == 0, f"W={SH.WARN} F={SH.FAIL}")

# success records nothing
SH.FAIL.clear(); SH.WARN.clear()
SH.check("fine", True)
expect("passing check records nothing",
       not SH.FAIL and not SH.WARN, f"F={SH.FAIL} W={SH.WARN}")

print("\nthreshold logic")
# the $0.00 income condition — this is the silent failure it must catch
SH.FAIL.clear(); SH.WARN.clear()
SH.check("income loop yield", False, "246 ship events, $0.00", warn_only=True)
expect("zero-revenue-with-many-ships is flagged",
       any("0.00" in w for w in SH.WARN), f"{SH.WARN}")

# but a genuinely earning loop must NOT be flagged
SH.WARN.clear()
SH.check("income loop yield", True, "10 ships, $12.50")
expect("earning loop is not flagged", not SH.WARN, f"{SH.WARN}")

print("\nreal status file reflects reality")
hp = Path("/root/evez-agentnet/status/HEALTH.md")
expect("HEALTH.md exists", hp.exists())
if hp.exists():
    txt = hp.read_text()
    expect("HEALTH.md names the zero-revenue finding", "$0.00" in txt)
    # The public-gateway warning was CLOSED on 2026-10-02
    # (openclaw-public-forward disabled, verified unreachable from outside).
    # Asserting its presence here would fail the moment the fix landed,
    # which is the wrong contract. Assert the finding itself instead.
    # HEALTH.md is a PROBLEMS-ONLY document: it records failures and warnings,
    # and deliberately omits passing checks. So a clean gateway must NOT
    # appear. Asserting "gateway" is present would be asserting the bug.
    expect("clean gateway is omitted from the problems doc",
           "socat forwarding" not in txt,
           "a passing check should not be listed as a problem")
    # subprocess.run(...).stdout is a single string; unpacking it into two
    # values yields None and crashes the test. Same mistake as the one the
    # gateway test just caught in generate_brief.py.
    _out = __import__("subprocess").run(
        "ss -tlnp 2>/dev/null | grep socat | grep -vE '127\\.0\\.0\\.1|100\\.126\\.' || true",
        shell=True, capture_output=True, text=True).stdout or ""
    public_open = [l for l in _out.splitlines() if l.strip()]
    expect("HEALTH.md agrees with the live socket state",
           ("socat forwarding" in txt) == bool(public_open),
           f"warned={('socat forwarding' in txt)} live_public={bool(public_open)}")

import json
sj = Path("/root/evez-agentnet/status/HEALTH.json")
expect("HEALTH.json is valid JSON",
       json.loads(sj.read_text()) if sj.exists() else False)

print("\nopen items must be surfaced, and closed ones must not linger")
if hp.exists():
    t = hp.read_text().lower()
    # The clawhub token was rotated/cleaned from the tree (real-token grep
    # is CLEAN). The check is now conditional on the same evidence the
    # health check uses: a watchdog must re-open the finding IF AND ONLY IF
    # a real token is present again, not keep a stale warning alive forever.
    import subprocess as _sp
    _rc = _sp.run(
        "grep -rEq 'clh_[A-Za-z0-9_-]{20,}' /root/evez-agentnet "
        "--include='*.py' 2>/dev/null | grep -vE 'TESTONLY|SYNTHETIC'",
        shell=True, capture_output=True, text=True)
    real_token_present = _rc.returncode == 0 and bool(_rc.stdout.strip())
    expect("flags clawhub token",
           ("clawhub" in t) if real_token_present else ("clawhub" not in t),
           f"real_token_present={real_token_present} "
           f"warned={'clawhub' in t}")
    expect("flags zero revenue", "0.00" in t)
    # public gateway was resolved; it should NOT be re-flagged while clean
    expect("does not re-flag the resolved public gateway",
           "socat forwarding" not in t,
           "stale warning for an exposure that is now closed")

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
