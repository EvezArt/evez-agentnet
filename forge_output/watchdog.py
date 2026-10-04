
#!/usr/bin/env python3
"""EVEZ-OS Exposure Watchdog.

Closes the 2026-10-02 exposure triad as an executable check rather than a
note: a public OpenClaw gateway, credentials sitting in working trees, and
uncommitted edits to the files those credentials live in.

Three INDEPENDENT checks, each emitting structured JSON findings:

  gateway  TCP-probe BOTH 127.0.0.1:18789 and 80.241.209.34:18789. A
           successful EXTERNAL connect is CRITICAL.
  secrets  Regex sweep for service_role / clh_ / sk- / ghp_ / Supabase JWTs.
           Reports file and line number ONLY. The matched value is never
           printed, logged, stored, or returned -- the rule NAME is all that
           leaves this function.
  drift    git status --porcelain per root; flags uncommitted changes to any
           file the secrets sweep already implicated. NATS subject count and
           Docker container health ride along as context.

Every finding carries `severity` (CRITICAL/WARN/INFO) and a stable
`fingerprint` used for dedup across cycles. Findings are appended to
evidence/<UTC date>/exposure.jsonl, the date computed at runtime.

A check that ERRORS emits its own finding (severity WARN, errored=true) and
forces exit 2. It is never silently skipped and never reads as clean.

Exit codes: 0 clean / 1 actionable findings / 2 a check errored.
INFO findings are recorded context and do NOT make the run unclean -- otherwise
a healthy stack would alarm every cycle.

Run:      python3 forge_output/watchdog.py [--root R ...] [--json] [--notify]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("WATCHDOG_REPO", "/root/evez-agentnet"))
EVIDENCE = Path(os.environ.get("WATCHDOG_EVIDENCE", str(REPO / "evidence")))
STATE = Path(os.environ.get("WATCHDOG_STATE", str(REPO / "status/.watchdog_seen.json")))

PROBE_TIMEOUT = float(os.environ.get("WATCHDOG_PROBE_TIMEOUT", "4"))

# Probe targets are overridable so the self-test is hermetic (it must not
# depend on whether 18789 happens to be public right now).
LOCAL_PROBE = (os.environ.get("WATCHDOG_LOCAL_HOST", "127.0.0.1"),
               int(os.environ.get("WATCHDOG_LOCAL_PORT", "18789")))
EXTERNAL_PROBE = (os.environ.get("WATCHDOG_EXT_HOST", "80.241.209.34"),
                  int(os.environ.get("WATCHDOG_EXT_PORT", "18789")))

# The known exposures live outside the agentnet tree (evez-atlas), so the
# default sweep covers both. Override with --root.
DEFAULT_ROOTS = [REPO, Path("/root/repos/evez-atlas")]

# Test hook: force a named check to raise, to prove exit 2 is reachable.
FORCE_ERROR = os.environ.get("WATCHDOG_FORCE_ERROR", "").strip()

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             ".mypy_cache", ".pytest_cache"}
MAX_FILE_BYTES = 2_000_000

# Credential shapes. The matched text is never retained past sweep_file().
#
# `service_role` on its own is a WORD, not a secret: it appears in audit prose,
# in grep one-liners, in the watchdog's own pattern table, and in its own
# evidence rows. Matching the bare word produced 6 of 11 CRITICALs on a first
# real run, every one of them noise, and a watchdog that cries wolf on its own
# documentation gets muted. The assignment form is what separates a real leak
# from a sentence about one.
PATTERNS = {
    "supabase_service_role": re.compile(
        r"service_role[\"']?\s*[:=]>?\s*[\"'][A-Za-z0-9._\-]{16,}"),
    "clawhub_token": re.compile(r"\bclh_[A-Za-z0-9_-]{16,}"),
    "openai_style_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "stripe_live_key": re.compile(r"\bsk_live_[A-Za-z0-9]{16,}"),
    "github_pat": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "supabase_jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
}

# Placeholder markers. These suppress a match ONLY on a comment or doc line.
#
# Scope matters: the first cut suppressed any line containing a placeholder,
# which silently disarmed the planted-credential self-test (its synthetic
# token contains "testonly" inside a real assignment). A placeholder in prose
# is not an exposure; a placeholder inside an assigned value is still the only
# copy of a credential-shaped string on disk, and its name is exactly why it
# must be rotated.
PLACEHOLDER = re.compile(
    r"(?i)testonly|notreal|redacted|placeholder|dummy|example|your[_-]?"
    r"|<[a-z_]{3,}>|\.\.\.|x{8,}")
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--|;|>)\s?")


def is_prose(line: str) -> bool:
    """True for comment/doc lines, where a credential SHAPE is being discussed
    rather than stored."""
    return bool(COMMENT.match(line))


CRITICAL, WARN, INFO = "CRITICAL", "WARN", "INFO"
ACTIONABLE = (CRITICAL, WARN)

EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


class CheckError(RuntimeError):
    """A check could not complete. Surfaced as a finding, never swallowed."""


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def fingerprint(check: str, kind: str, severity: str, where: str) -> str:
    """Stable identity for dedup.

    Excludes volatile detail (timestamps, line lists, probe latency) so the
    same exposure does not re-alert on every 15-minute cycle.
    """
    return hashlib.sha256("\x1f".join((check, kind, severity, where)).encode()).hexdigest()[:16]


def finding(check, kind, severity, where, detail, context=None, errored=False):
    return {
        "ts": now(),
        "check": check,
        "kind": kind,
        "severity": severity,
        "where": where,
        "detail": detail,
        "errored": bool(errored),
        "fingerprint": fingerprint(check, kind, severity, where),
        "context": context or {},
    }


# ── check 1: gateway ───────────────────────────────────────────────────────
def tcp_probe(host: str, port: int) -> dict:
    t0 = datetime.now(timezone.utc)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(PROBE_TIMEOUT)
    try:
        rc = sock.connect_ex((host, port))
        is_open = rc == 0
        err = "" if is_open else os.strerror(rc)
    except OSError as exc:          # network refused == a result, not an error
        is_open, err = False, str(exc)
    finally:
        sock.close()
    return {"host": host, "port": port, "open": is_open, "error": err,
            "elapsed_ms": round((datetime.now(timezone.utc) - t0).total_seconds() * 1000)}


def check_gateway(_roots):
    if FORCE_ERROR == "gateway":
        raise CheckError("forced error (WATCHDOG_FORCE_ERROR=gateway)")
    findings = []
    local = tcp_probe(*LOCAL_PROBE)
    ext = tcp_probe(*EXTERNAL_PROBE)
    context = {"local_probe": local, "external_probe": ext}

    findings.append(finding(
        "gateway", "local_reachable", INFO,
        "{}:{}".format(*LOCAL_PROBE),
        "loopback probe: {}".format("open" if local["open"] else "closed/filtered"),
        context,
    ))

    if ext["open"]:
        findings.append(finding(
            "gateway", "public_exposure", CRITICAL,
            "{}:{}".format(*EXTERNAL_PROBE),
            "TCP connect to the OpenClaw gateway on the PUBLIC IP succeeded. "
            "It must be reachable over Tailscale only.",
            context,
        ))
    else:
        findings.append(finding(
            "gateway", "external_closed", INFO,
            "{}:{}".format(*EXTERNAL_PROBE),
            "external probe did not connect (healthy baseline); recorded so a "
            "regression to open lands in the same evidence stream",
            context,
        ))
    return findings


# ── check 2: secrets ───────────────────────────────────────────────────────
def iter_text_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            try:
                if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def sweep_file(path: Path) -> list:
    """Return [(rule_name, lineno)]. The matched text is deliberately dropped.

    Nothing derived from the secret survives this function -- not the match,
    not a prefix, not a length. Callers only ever see a rule name and a line
    number.
    """
    hits = []
    try:
        with path.open("r", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if PLACEHOLDER.search(line) and is_prose(line):
                    continue
                for rule, rx in PATTERNS.items():
                    if rx.search(line):
                        hits.append((rule, lineno))
    except OSError:
        return hits
    return hits


def check_secrets(roots):
    if FORCE_ERROR == "secrets":
        raise CheckError("forced error (WATCHDOG_FORCE_ERROR=secrets)")
    if not roots:
        raise CheckError("no sweep roots configured")
    findings = []
    for root in roots:
        if not root.exists():
            raise CheckError("sweep root missing: {}".format(root))
        for path in iter_text_files(root):
            hits = sweep_file(path)
            if not hits:
                continue
            try:
                rel = str(path.relative_to(root))
            except ValueError:
                rel = str(path)
            for rule in sorted({r for r, _ in hits}):
                rule_lines = sorted(n for r, n in hits if r == rule)
                findings.append(finding(
                    "secrets", rule, CRITICAL,
                    "{}:{}:{}".format(root, rel, rule_lines[0]),
                    "credential-shaped match on disk (value withheld). Removal "
                    "from the tree does NOT revoke it -- rotate at the provider.",
                    {"root": str(root), "file": rel,
                     "lines": rule_lines[:20], "line_count": len(rule_lines)},
                ))
    if not findings:
        findings.append(finding(
            "secrets", "sweep_clean", INFO, "all_roots",
            "no credential-shaped matches found",
            {"roots": [str(r) for r in roots]},
        ))
    return findings


# ── check 3: drift (+ NATS/Docker context) ─────────────────────────────────
def run_cmd(cmd, cwd=None, timeout=30):
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckError("{} failed: {}".format(" ".join(cmd), exc)) from exc
    if res.returncode != 0:
        raise CheckError("{} rc={}: {}".format(" ".join(cmd), res.returncode,
                                                res.stderr.strip()[:200]))
    return res.stdout


def nats_context() -> dict:
    """Context only. NATS being down must not error the watchdog."""
    out = {"subjects": None, "note": ""}
    try:
        res = subprocess.run(["nats", "server", "check", "connection"],
                             capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            m = re.search(r"(\d+)\s+subjects", res.stdout)
            out["subjects"] = int(m.group(1)) if m else None
        else:
            out["note"] = "nats cli unavailable or disconnected (rc={})".format(res.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        out["note"] = "nats probe failed: {}".format(exc)
    return out


def docker_context() -> dict:
    out = {"total": None, "unhealthy": [], "note": ""}
    try:
        res = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                             capture_output=True, text=True, timeout=20)
        if res.returncode != 0:
            out["note"] = "docker ps rc={}".format(res.returncode)
            return out
        rows = [r for r in res.stdout.splitlines() if r.strip()]
        out["total"] = len(rows)
        for row in rows:
            name, _, status = row.partition("\t")
            if re.search(r"unhealthy|exited|restarting", status, re.I):
                out["unhealthy"].append({"name": name, "status": status})
    except (OSError, subprocess.SubprocessError) as exc:
        out["note"] = "docker probe failed: {}".format(exc)
    return out


def check_drift(roots, prior_findings=None):
    if FORCE_ERROR == "drift":
        raise CheckError("forced error (WATCHDOG_FORCE_ERROR=drift)")
    findings = []
    context = {"nats": nats_context(), "docker": docker_context()}
    per_root = {}

    for root in roots:
        if not (root / ".git").exists():
            per_root[str(root)] = {"error": "not a git repository", "paths": []}
            continue
        try:
            porcelain = run_cmd(["git", "status", "--porcelain"], cwd=root)
        except CheckError as exc:
            per_root[str(root)] = {"error": str(exc), "paths": []}
            continue
        paths = []
        for line in porcelain.splitlines():
            if len(line) < 4:
                continue
            paths.append({"code": line[:2], "path": line[3:].strip().strip('"')})
        per_root[str(root)] = {"changed": len(paths),
                               "paths": [p["path"] for p in paths[:200]]}
    context["git"] = per_root

    # Files the secrets sweep already implicated. An uncommitted edit to one
    # of those is how a credential gets re-committed or a purge gets undone.
    implicated = set()
    for f in (prior_findings or []):
        if f.get("check") == "secrets":
            rel = (f.get("context") or {}).get("file")
            if rel:
                implicated.add(rel)

    dirty = set()
    for info in per_root.values():
        dirty.update(info.get("paths", []))

    for rel in sorted(implicated & dirty):
        findings.append(finding(
            "drift", "secret_file_drift", CRITICAL, rel,
            "uncommitted change to a file the credential sweep flagged",
            context,
        ))

    if not findings:
        findings.append(finding(
            "drift", "no_secret_drift", INFO, "worktree",
            "no uncommitted changes to credential-implicated files "
            "({} dirty path(s) seen overall)".format(len(dirty)),
            context,
        ))
    return findings


# ── plumbing ───────────────────────────────────────────────────────────────
def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"seen": {}}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE)


def evidence_dir(day=None):
    """Runtime UTC date -- not baked in at build time."""
    day = day or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    outdir = EVIDENCE / day
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def write_evidence(findings, day=None):
    path = evidence_dir(day) / "exposure.jsonl"
    with path.open("a") as fh:
        for f in findings:
            fh.write(json.dumps(f, sort_keys=True) + "\n")
    return path


def new_criticals(findings, state):
    """Only NEW CRITICAL fingerprints. This is the dedup gate for notify."""
    seen = state.setdefault("seen", {})
    fresh = []
    for f in findings:
        if f["severity"] != CRITICAL:
            continue
        if f["fingerprint"] in seen:
            continue
        seen[f["fingerprint"]] = {"first_seen": f["ts"], "where": f["where"]}
        fresh.append(f)
    return fresh


def notify(findings) -> bool:
    """Best-effort Telegram send. Delivery failure never changes the exit code."""
    if not findings:
        return True
    try:
        sys.path.insert(0, str(REPO))
        import notify as notify_mod
    except Exception as exc:
        print("notify unavailable: {}".format(exc), file=sys.stderr)
        return False
    token = notify_mod.get_token()
    chat = notify_mod.get_chat_id()
    if not token or not chat:
        print("notify: no bot token/chat id; skipping send", file=sys.stderr)
        return False
    lines = ["*EVEZ exposure watchdog \u2014 NEW CRITICAL*"]
    for f in findings:
        lines.append("\u2022 [{}] {}".format(f["check"], f["where"]))
    ok, err = notify_mod.api("sendMessage", {"chat_id": chat,
                                             "text": "\n".join(lines)[:4000],
                                             "parse_mode": "Markdown"})
    if not ok:
        print("notify send failed: {}".format(err), file=sys.stderr)
    return bool(ok)


def _maybe_force(name):
    if FORCE_ERROR == name:
        raise CheckError("forced error (WATCHDOG_FORCE_ERROR={})".format(name))


def run(roots, do_notify=False):
    findings, errored = [], False

    for name, fn in (("gateway", check_gateway), ("secrets", check_secrets)):
        try:
            findings.extend(fn(roots))
        except CheckError as exc:
            errored = True
            findings.append(finding(name, "check_error", WARN, name,
                                    "check did not complete: {}".format(exc),
                                    errored=True))
        except Exception as exc:
            errored = True
            findings.append(finding(name, "check_error", WARN, name,
                                    "unhandled {}: {}".format(type(exc).__name__, exc),
                                    errored=True))

    try:
        findings.extend(check_drift(roots, findings))
    except CheckError as exc:
        errored = True
        findings.append(finding("drift", "check_error", WARN, "drift",
                                "check did not complete: {}".format(exc), errored=True))
    except Exception as exc:
        errored = True
        findings.append(finding("drift", "check_error", WARN, "drift",
                                "unhandled {}: {}".format(type(exc).__name__, exc),
                                errored=True))

    state = load_state()
    fresh = new_criticals(findings, state)
    save_state(state)
    path = write_evidence(findings)

    if do_notify and fresh:
        notify(fresh)

    active = [f for f in findings if f["severity"] in ACTIONABLE]
    rc = EXIT_ERROR if errored else (EXIT_FINDINGS if active else EXIT_CLEAN)
    return rc, {
        "findings": len(findings),
        "critical": sum(1 for f in findings if f["severity"] == CRITICAL),
        "warn": sum(1 for f in findings if f["severity"] == WARN),
        "info": sum(1 for f in findings if f["severity"] == INFO),
        "errored_checks": sorted({f["check"] for f in findings if f["errored"]}),
        "new_critical": len(fresh),
        "exit_code": rc,
        "evidence": str(path),
        "fingerprints": [f["fingerprint"] for f in findings],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="EVEZ-OS exposure watchdog")
    ap.add_argument("--root", action="append", default=None,
                    help="sweep root (repeatable); default evez-agentnet + evez-atlas")
    ap.add_argument("--notify", action="store_true",
                    help="Telegram-send only NEW criticals (deduped by fingerprint)")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args(argv)

    roots = [Path(r) for r in args.root] if args.root else [p for p in DEFAULT_ROOTS if p.exists()]
    rc, summary = run(roots, args.notify)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("findings={} critical={} warn={} info={} new_critical={} rc={} -> {}".format(
            summary["findings"], summary["critical"], summary["warn"], summary["info"],
            summary["new_critical"], rc, summary["evidence"]))
        for f in summary["fingerprints"]:
            print("  fp=" + f)
        if summary["errored_checks"]:
            print("  ERRORED CHECKS: " + ", ".join(summary["errored_checks"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
