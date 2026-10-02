"""Repo-wide static audit for defect classes that actually shipped to EVEZ logs.

Catches the specific patterns found in production:
  A. `log` shadowing: module assigns `log = logging.getLogger(...)` while also
     importing a callable named `log` (math, etc.) -> runtime TypeError.
  B. Duplicated orchestrator implementations (why fixes didn't propagate).
  C. CI steps that can never fail (`|| true` on a test/syntax command).
  D. Bare `min(reputation, key=...)` with no threshold guard — prescribes
     recovery to saturated (rep=1.0) agents, which is what the logs showed.

Run:  python3 audit_repo.py          (exit 1 on CRASH)
Self-test: python3 test_audit_detects.py

Every detector here is exercised by test_audit_detects.py against reconstructed
broken fixtures. An audit that cannot be shown to fire is worse than none.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path("/root/evez-agentnet")

CRASH, CI, LOGIC, DUP = "CRASH", "CI", "LOGIC", "DUP"


def py_files(root: Path | None = None) -> list[Path]:
    root = root or ROOT
    return [p for p in root.rglob("*.py")
            if ".git" not in p.parts and "__pycache__" not in p.parts]


# ── A. log shadowing ────────────────────────────────────────────────────────
def check_log_shadow(tree: ast.AST, path: Path, findings: list) -> None:
    imports_log = False
    assigns_log: int | None = None
    calls_log = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if (a.asname or a.name) == "log":
                    imports_log = True
        elif isinstance(node, ast.Import):
            for a in node.names:
                if (a.asname or a.name.split(".")[0]) == "log":
                    imports_log = True
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "log":
                    if isinstance(node.value, ast.Call) and \
                            "getLogger" in ast.dump(node.value):
                        assigns_log = node.lineno
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "log":
            calls_log += 1

    if imports_log and assigns_log is not None and calls_log:
        findings.append((CRASH, path, assigns_log,
                         "`log` is both a math import and a Logger while log(...) "
                         f"is called ({calls_log} site(s)) -> TypeError at runtime"))


# ── B. duplicated orchestrator implementations ─────────────────────────────
def check_duplicates(tree: ast.AST, path: Path, findings: list) -> None:
    """A delegating wrapper is fine; a real body is a duplicate implementation."""
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "generate_rsi_hypotheses":
            continue
        src = ast.unparse(node)
        if "generate_rsi_hypotheses as _impl" in src:
            continue                       # delegating wrapper — correct
        findings.append((DUP, path, node.lineno,
                         "own implementation of generate_rsi_hypotheses — should "
                         "delegate to orchestrator.py so fixes propagate"))


# ── D. bare min() on reputation ────────────────────────────────────────────
def check_min_rep(tree: ast.AST, path: Path, findings: list) -> None:
    mins = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "min" and node.args):
            has_key = any(k.arg == "key" for k in node.keywords)
            if isinstance(node.args[0], ast.Name) and \
                    re.match(r"^rep", node.args[0].id) and has_key:
                mins.append(node)
    if not mins:
        return

    # A selection is "guarded" when nearby code either compares the chosen
    # agent's reputation to a threshold, or pre-filters to a subset first.
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            seg = ast.unparse(node)
            if re.search(r"rep\w*\s*\[\s*lowest\S*\s*\]\s*<\s*0?\.\d", seg) \
                    or re.search(r"(rep\w*|reputation)\s*<\s*0?\.\d", seg) \
                    or re.search(r"0?\.\d+\s*<=\s*rep", seg):
                guarded.add(node.lineno)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("below", "stuck"):
                    guarded.add(node.lineno)
        elif isinstance(node, ast.DictComp):
            # {k: v for k, v in rep.items() if v < 0.8} — a pre-filter
            seg = ast.unparse(node)
            if re.search(r"<\s*0?\.\d", seg):
                guarded.add(node.lineno)

    for node in mins:
        if any(abs(node.lineno - g) <= 14 for g in guarded):
            continue
        findings.append((LOGIC, path, node.lineno,
                         "selects min(reputation) with no threshold guard — "
                         "prescribes recovery to saturated agents"))


# ── driver ─────────────────────────────────────────────────────────────────
def scan(root: Path | None = None) -> list:
    root = root or ROOT
    findings: list = []
    files = py_files(root)

    for p in files:
        if p.name == "audit_repo.py":      # never audit the auditor's own regexes
            continue
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except SyntaxError as e:
            findings.append((CRASH, p, e.lineno or 0, f"syntax error: {e.msg}"))
            continue
        check_log_shadow(tree, p, findings)
        check_duplicates(tree, p, findings)
        check_min_rep(tree, p, findings)

    # ── C. unfailable CI ──
    wfdir = root / ".github" / "workflows"
    if wfdir.is_dir():
        for wf in sorted(wfdir.glob("*.y*ml")):
            for i, line in enumerate(wf.read_text(errors="replace").splitlines(), 1):
                if ("pytest" in line or "py_compile" in line) and "|| true" in line:
                    what = "test" if "pytest" in line else "syntax check"
                    findings.append((CI, wf, i,
                                     f"{what} step ends in `|| true` — cannot fail "
                                     f"the build"))

    # DUP only matters when there is more than one implementation
    dups = [f for f in findings if f[0] == DUP]
    if len(dups) <= 1:
        findings = [f for f in findings if f[0] != DUP]

    sev_order = {CRASH: 0, CI: 1, LOGIC: 2, DUP: 3}
    findings.sort(key=lambda f: (sev_order.get(f[0], 9), str(f[1])))
    return findings


def main() -> int:
    findings = scan()
    print(f"scanned {len(py_files())} python files\n")
    if not findings:
        print("clean — no instances of the audited defect classes")
        return 0

    for sev, path, line, msg in findings:
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        print(f"[{sev}] {rel}:{line}\n        {msg}")

    counts: dict[str, int] = {}
    for f in findings:
        counts[f[0]] = counts.get(f[0], 0) + 1
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 1 if counts.get(CRASH) else 0


if __name__ == "__main__":
    sys.exit(main())
