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
    expect("HEALTH.md names the public-gateway exposure", "public IP" in txt)

import json
sj = Path("/root/evez-agentnet/status/HEALTH.json")
expect("HEALTH.json is valid JSON",
       json.loads(sj.read_text()) if sj.exists() else False)

print("\nthe three known open items must all still be surfaced")
if hp.exists():
    t = hp.read_text().lower()
    expect("flags public gateway", "public" in t)
    expect("flags clawhub token", "clawhub" in t)
    expect("flags zero revenue", "0.00" in t)

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
