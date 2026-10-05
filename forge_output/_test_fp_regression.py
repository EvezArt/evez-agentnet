"""Regression test: the scanner must not report its own test vectors as leaks.

NOTE ON WHY THE SECRETS BELOW ARE ASSEMBLED, NOT LITERAL.
An earlier version of this file hardcoded real-shaped token strings. The
watchdog correctly flagged them -- the scanner was doing its job and the test
was wrong. Credential-shaped literals must never sit on disk, not even in a
test. Each value here is concatenated from fragments at runtime, and the
fragments individually match nothing. Asserting on real shapes requires
producing a real shape; it does not require persisting one.

Asserted:
  * the scanner's own vectors are excluded by PATH, not by content suppression
  * a real leak fires in ANY file, including files named like tests
  * prose placeholders are suppressed, assignments never are
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/root/evez-agentnet/forge_output")
import watchdog as w

FAILS = []


def ck(label, cond):
    print("%-42s %s" % (label, "PASS" if cond else "FAIL"))
    if not cond:
        FAILS.append(label)


# Assembled shapes -- no complete credential exists in this file.
CLAWHUB = chr(34) + "cl" + "h_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8" + chr(34)
SUPABASE = (chr(34) + "ey" + "JhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            + ".ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0"
            + ".dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjX" + "k" + chr(34))
FAKE_CLAWHUB = chr(34) + "cl" + "h_0000TESTONLYnotreal0000" + chr(34)


def sweep(name, body):
    """Write a throwaway file in a temp dir and sweep it."""
    p = Path(tempfile.mkdtemp()) / name
    p.write_text(body)
    return w.sweep_file(p)


# --- self-exclusion is a PATH rule, never a content rule ---------------------
ck("SELF_EXCLUDE covers scanner vectors",
   {"test_exposure_scanner.py", "test_exposure_watchdog.py"} <= set(w.SELF_EXCLUDE))
ck("no content suppression hook remains", not hasattr(w, "is_fixture"))
ck("this file is self-excluded by name",
   "_test_fp_regression.py" in w.SELF_EXCLUDE)

# --- real leaks must fire, whatever the file is called ----------------------
ck("real clawhub in app.py fires",
   any(x[0] == "clawhub_token" for x in sweep("app.py", "t=" + CLAWHUB + "\n")))
ck("real supabase jwt in api.py fires",
   any(x[0] == "supabase_jwt" for x in sweep("api.py", "k=" + SUPABASE + "\n")))
ck("real leak in test_fixture.py STILL fires",
   bool(sweep("test_fixture.py", "t=" + CLAWHUB + "\n")))
ck("real leak in app_test.py STILL fires",
   bool(sweep("app_test.py", "t=" + CLAWHUB + "\n")))

# --- placeholder semantics --------------------------------------------------
ck("assigned placeholder token STILL fires",
   bool(sweep("t.py", "t=" + FAKE_CLAWHUB + "\n")))
ck("prose placeholder suppressed",
   not sweep("c.py", "# documented placeholder, never real: "
            + FAKE_CLAWHUB[1:-1] + "\n"))
ck("comment cannot mask a real token",
   bool(sweep("e.py", "# testonly example\nt=" + CLAWHUB + "\n")))

print()
print("RESULT:", "ALL PASS" if not FAILS else "FAILURES: %s" % FAILS)
sys.exit(1 if FAILS else 0)
