"""Prove audit_repo.py is not vacuously green.

Reconstructs each defect class it claims to detect, in a temp directory, and
asserts the audit fires. Also asserts the real repo is clean AND that the
detectors still fire on a copy of the repo with a bug reintroduced.

An audit that never fires is worse than no audit — it manufactures confidence.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/root/evez-agentnet")
import audit_repo as A

REPO = Path("/root/evez-agentnet")

FIXTURES = {
    "log_shadow": ("""\
import logging
from math import log
log = logging.getLogger("x")
def f(p):
    return -sum(p * log(p) for p in p)
""", A.CRASH),

    "syntax_error": (
        "def f():\n    try:\n        x = 1\n            y = 2\n    else:\n        pass\n",
        A.CRASH),

    "bare_min_rep": ("""\
def gen(state):
    rep = {k: v["reputation"] for k, v in state["agents"].items()}
    lowest = min(rep, key=rep.get)
    return [f"Evolve {lowest} agent: reputation={rep[lowest]:.2f} -> recover via streak"]
""", A.LOGIC),

    # Duplication means MORE THAN ONE own implementation. The detector
    # deliberately stays silent on a single implementation, because that is
    # normal for the canonical module.
    "duplicate_impl": None,   # handled as a two-file case below
}

NEGATIVES = {
    "guarded_min_rep": ("""\
def gen(state):
    rep = {k: v["reputation"] for k, v in state["agents"].items()}
    below = {k: v for k, v in rep.items() if v < 0.80}
    if below:
        lowest = min(below, key=below.get)
        return [f"recover {lowest}"]
    return []
""", A.LOGIC),

    "delegating_wrapper": ("""\
def generate_rsi_hypotheses(state):
    \"\"\"Delegates.\"\"\"
    from orchestrator import generate_rsi_hypotheses as _impl
    return _impl(state)
""", A.DUP),

    "logger_only": ("""\
import logging
log = logging.getLogger("x")
def f():
    log.info("hi")
    return 1
""", A.CRASH),
}


def run_case(text: str) -> set[str]:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "fixture.py").write_text(text)
        return {f[0] for f in A.scan(root)}


def main() -> int:
    failed = 0

    print("positive — audit must fire:")
    for name, spec in FIXTURES.items():
        if spec is None:
            continue
        text, expected = spec
        sevs = run_case(text)
        if expected in sevs:
            print(f"  ok   {name}: detected {expected}")
        else:
            print(f"  FAIL {name}: expected {expected}, got {sorted(sevs) or 'nothing'}")
            failed += 1

    # duplication needs two independent implementations across files
    impl = """\
def generate_rsi_hypotheses(state):
    rep = {k: v["reputation"] for k, v in state["agents"].items()}
    return [str(min(rep, key=rep.get))]
"""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "a.py").write_text(impl)
        (root / "b.py").write_text(impl)
        sevs = {f[0] for f in A.scan(root)}
        if A.DUP in sevs:
            print("  ok   duplicate_impl: detected DUP across two files")
        else:
            print(f"  FAIL duplicate_impl: expected DUP, got {sorted(sevs) or 'nothing'}")
            failed += 1

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "a.py").write_text(impl)   # only ONE implementation
        sevs = {f[0] for f in A.scan(root)}
        if A.DUP not in sevs:
            print("  ok   single_impl: no false DUP")
        else:
            print("  FAIL single_impl: false DUP on a lone implementation")
            failed += 1

    print("\nnegative — audit must stay silent on correct code:")
    for name, (text, forbidden) in NEGATIVES.items():
        sevs = run_case(text)
        if forbidden not in sevs:
            print(f"  ok   {name}: no false positive")
        else:
            print(f"  FAIL {name}: false positive {forbidden}")
            failed += 1

    print("\nunfailable CI detector, against real workflows:")
    ci = [f for f in A.scan() if f[0] == A.CI]
    if ci:
        print(f"  FAIL ci.yml still has unfailable steps: {[(str(f[1]), f[2]) for f in ci]}")
        failed += 1
    else:
        print("  ok   no `|| true` test steps in any workflow")

    print("\nwhole-repo scan:")
    findings = A.scan()
    real = [f for f in findings if "fixture" not in str(f[1])]
    if real:
        print(f"  FAIL repo not clean:")
        for sev, path, line, msg in real:
            print(f"        [{sev}] {Path(path).name}:{line} {msg}")
        failed += 1
    else:
        print("  ok   repo clean across all four detectors")

    print("\nnegative control — reintroduce a bug into a repo copy, expect detection:")
    with tempfile.TemporaryDirectory() as d:
        dst = Path(d) / "repo"
        shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.jsonl", "drafts", "spine"))
        broken = dst / "agents" / "rsi_engine.py"
        src = broken.read_text()
        broken.write_text(src + """


def _reintroduced_bug(state):
    rep = {k: v.get("reputation", 0.9) for k, v in state.get("agents", {}).items()}
    lowest = min(rep, key=rep.get)
    return [f"Inject synthetic recovery into '{lowest}' rep={rep[lowest]:.2f}"]
""")
        got = [f for f in A.scan(dst) if f[0] == A.LOGIC and "rsi_engine" in str(f[1])]
        if got:
            print(f"  ok   detected reintroduced bug at {Path(str(got[0][1])).name}:{got[0][2]}")
        else:
            print("  FAIL auditor did not catch a bug planted in a copy of the repo")
            failed += 1

    print(f"\n{'AUDIT SELF-TEST PASSED' if not failed else f'{failed} CHECK(S) FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
