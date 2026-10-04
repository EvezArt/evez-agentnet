#!/usr/bin/env python3
"""EVEZ-OS STAMP -- Standing Trace of Action, Model Provenance.

A provenance daemon for agent swarms. Everything else in this repo records
WHAT the stack did. STAMP records the four things nothing else records:

  * what an agent CLAIMED versus what a machine ACTUALLY returned
  * what was asserted and never checked at all (unverified claims)
  * what was raised and never resolved (open questions, open findings)
  * what happened when a tool failed (error CLASS, never the error string)

That gap is where honesty training data lives, and it is the one signal a
self-referential swarm cannot generate about itself: an agent cannot report
its own unverified claims, because by definition it did not notice them.

PRIVACY INVARIANT (the build fails if this is broken)
-----------------------------------------------------
STAMP NEVER records, logs, prints or writes the CONTENT of a human message, a
question, an assistant response, a tool argument, or a finding. It records
only metadata: event kind, UTC timestamp, entity id (a file path or task id --
never a content hash), age in seconds, and derived counts. No verbatim quotes,
no substrings, no body hashes, no truncated previews. test_stamp.py plants a
sentinel string in an event body and asserts it appears nowhere in any output
file, stdout or stderr.

MODULES
-------
  ingest    JSONL events on stdin / --events, plus a --transcript adapter that
            turns a real Hermes session transcript into metadata-only events
  corpus    pairs claim_made with the tool_result that verified or
            contradicted it -> verified / contradicted / unverified rows
  absence   staleness buckets, unanswered_ratio, abandonment_rate,
            session_ended_abruptly, correction_weight
  dedup     16-hex fingerprint over stable fields only (no timestamps), so a
            persistent gap does not re-alert every cycle
  chain     SHA-256 hash chain over every record; chain head in a state file;
            --verify recomputes the whole chain and exits nonzero if broken

EVIDENCE
--------
Findings append to evidence/<UTC date>/exposure.jsonl -- the same file the
exposure watchdog uses, in the same JSON shape, so the two streams interleave.
Exit codes: 0 clean / 1 findings present / 2 a module errored. A module that
ERRORS emits its own WARN finding with errored=true and never reads as clean.

Run:  python3 forge_output/stamp.py [--events F]... [--transcript F]...
                              [--json] [--verify] [--notify]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("STAMP_REPO", "/root/evez-agentnet"))
EVIDENCE = Path(os.environ.get("STAMP_EVIDENCE", str(REPO / "evidence")))
STATE = Path(os.environ.get("STAMP_STATE", str(REPO / "status/.stamp_state.json")))
CHAIN = Path(os.environ.get("STAMP_CHAIN", str(REPO / "status/.stamp_chain.jsonl")))
TRANSCRIPTS = Path(os.environ.get("STAMP_TRANSCRIPTS",
                                  "/root/.hermes/cache/delegation/live"))

# Test hook: force a named module to raise, to prove exit 2 is reachable.
FORCE_ERROR = os.environ.get("STAMP_FORCE_ERROR", "").strip()

CRITICAL, WARN, INFO = "CRITICAL", "WARN", "INFO"
ACTIONABLE = (CRITICAL, WARN)
EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2

GENESIS = "0" * 64

KNOWN_KINDS = {
    "claim_made", "tool_result", "question_open", "question_closed",
    "finding_raised", "finding_closed", "session_start", "session_ended",
    "correction_given", "correction_applied", "tool_failure",
}

ERROR_CLASSES = {"transport", "parse", "permission", "not_found", "timeout",
                 "resource", "unknown"}


class ModuleError(RuntimeError):
    """A STAMP module could not complete. Surfaced as a finding, never hidden."""


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_ts(value):
    """Parse an event timestamp to an aware UTC datetime. Never echoes input."""
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.fromisoformat(text[:19])
        except ValueError:
            return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,59}$")


def safe_slug(value) -> str:
    """Reduce a label to a bounded identifier.

    claim_type is metadata, but an event field is an untrusted channel: a
    producer that puts prose in claim_type must not thereby get prose into the
    evidence stream. Anything that is not already an identifier-like token is
    coerced to "unspecified" rather than sanitised-and-truncated, because a
    truncated fragment of a sentence is still a fragment of a sentence.
    """
    text = str(value).strip().lower()
    return text if SAFE_SLUG.match(text) else "unspecified"


def fingerprint(check: str, kind: str, severity: str, where: str) -> str:
    """Stable identity for dedup -- 16 hex.

    Computed from stable fields ONLY. Timestamps, durations, counts and ages
    are deliberately excluded so a gap that is still open tomorrow hashes
    identically to the one flagged today.
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


# ===========================================================================
# MODULE 1 -- ingest
# ===========================================================================
def normalise_event(raw: dict, source: str = "stdin") -> dict:
    """Project an arbitrary JSON object onto the STAMP event schema.

    Only whitelisted metadata keys survive. Anything else on the object -- a
    body, a prompt, a tool argument, a preview -- is DROPPED here and never
    reaches a module, a state file or an evidence row.
    """
    if not isinstance(raw, dict):
        raise ModuleError("event is not a JSON object ({})".format(type(raw).__name__))
    kind = str(raw.get("kind") or raw.get("event") or "").strip()
    if kind not in KNOWN_KINDS:
        raise ModuleError("unrecognised event kind")

    ev = {
        "kind": kind,
        "ts": parse_ts(raw.get("ts") or raw.get("timestamp")).isoformat(),
        "source": source,
    }
    entity = raw.get("entity_id") or raw.get("entity")
    if entity is not None:
        text = str(entity).strip()
        # A file path or task id is the permitted shape. A long free-text blob
        # is not an entity id, so it is rejected rather than truncated.
        ev["entity_id"] = text[:300] if re.match(r"^[A-Za-z0-9._:/#@\[\]-]+$", text) \
            else "unidentifiable"
    if raw.get("claim_type") is not None:
        ev["claim_type"] = safe_slug(raw["claim_type"])
    if raw.get("confidence") is not None:
        try:
            ev["confidence"] = float(raw["confidence"])
        except (TypeError, ValueError):
            ev["confidence"] = None
    if raw.get("ok") is not None:
        ev["ok"] = bool(raw["ok"])
    if raw.get("exit_code") is not None:
        try:
            ev["exit_code"] = int(raw["exit_code"])
        except (TypeError, ValueError):
            ev["exit_code"] = None
    if raw.get("duration_ms") is not None:
        try:
            ev["duration_ms"] = float(raw["duration_ms"])
        except (TypeError, ValueError):
            ev["duration_ms"] = None
    if raw.get("abrupt") is not None:
        ev["abrupt"] = bool(raw["abrupt"])
    if raw.get("resolved") is not None:
        ev["resolved"] = bool(raw["resolved"])
    if raw.get("closed_gap") is not None:
        ev["closed_gap"] = bool(raw["closed_gap"])
    if raw.get("error_class") is not None:
        cls = str(raw["error_class"]).strip().lower()
        ev["error_class"] = cls if cls in ERROR_CLASSES else "unknown"
    return ev


def read_jsonl(path: Path, source: str):
    events = []
    with path.open("r", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                raise ModuleError("unparseable JSON at line {}".format(lineno))
            events.append(normalise_event(raw, source=source))
    return events


def load_events(paths, stdin_text=None):
    """Load + sort events from --events paths and/or stdin JSONL."""
    events = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            raise ModuleError("events file not found: {}".format(path.name))
        events.extend(read_jsonl(path, source=path.name))
    if stdin_text:
        for lineno, line in enumerate(stdin_text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                raise ModuleError("unparseable JSON on stdin at line {}".format(lineno))
            events.append(normalise_event(raw, source="stdin"))
    events.sort(key=lambda e: (e["ts"], e["kind"]))
    return events


# -- transcript adapter: real Hermes session logs -> metadata-only events ----
# Field format of a live transcript line:
#     HH:MM:SS kind    | body...
# The body is NEVER copied into an event. Only the row KIND, the row TIME, an
# ordinal entity id and the ok/fail shape of a result survive.
LINE_RE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(\S+)\s*\|")
PATH_RE = re.compile(r"(/[A-Za-z0-9._/-]{3,200})")
DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*s\b")
RC_RE = re.compile(r"rc=(\d+)")

ERR_PATTERNS = (
    ("timeout", "timeout"), ("timed out", "timeout"),
    ("permission denied", "permission"), ("not permitted", "permission"),
    ("no such file", "not_found"), ("not found", "not_found"),
    ("traceback", "parse"), ("jsondecode", "parse"), ("syntaxerror", "parse"),
    ("connection", "transport"), ("refused", "transport"),
    ("timed", "timeout"), ("unreachable", "transport"),
    ("memoryerror", "resource"), ("no space", "resource"),
)


def classify_error(text: str) -> str:
    """Map a failure to a generic class. The message itself is discarded."""
    low = text.lower()
    for needle, cls in ERR_PATTERNS:
        if needle in low:
            return cls
    return "unknown"


def transcript_events(path: Path):
    """Convert one Hermes live transcript into metadata-only STAMP events."""
    day = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date()
    events = []
    tool_n = 0
    claim_n = 0
    # entity_id of the artifact the LAST tool call touched, so a claim and the
    # result that checks it share an id. A file PATH is a permitted entity id.
    open_claim = None          # entity awaiting verification
    last_tool_entity = None
    pending_tools = []         # entities awaiting a result row
    first_ts = None
    had_failure = False
    saw_end = False

    def mk(kind, ts, **kw):
        base = {"kind": kind, "ts": ts, "source": path.name}
        base.update(kw)
        return normalise_event(base, source=path.name)

    with path.open("r", errors="replace") as fh:
        for line in fh:
            m = LINE_RE.match(line)
            if not m:
                continue
            clock, kind = m.group(1), m.group(2).strip().lower()
            stamp = "{}T{}Z".format(day.isoformat(), clock)
            if first_ts is None:
                first_ts = stamp
                events.append(mk("session_start", stamp,
                                 resolved=None, entity_id=path.parent.name))

            body = line.split("|", 1)[1] if "|" in line else ""

            if kind == "tool":
                tool_n += 1
                found = PATH_RE.findall(body)
                entity = found[0] if found else "tool#{}".format(tool_n)
                pending_tools.append(entity)
                last_tool_entity = entity
            elif kind == "result":
                entity = pending_tools.pop(0) if pending_tools else (last_tool_entity or "tool")
                ok = "error" not in body[:200].lower()
                dur = DUR_RE.search(body[:200])
                ok_flag = "ok" in body[:200].lower()
                dur_ms = float(dur.group(1)) * 1000 if dur else None
                rc = RC_RE.search(body[:200])
                events.append(mk("tool_result", stamp, entity_id=entity,
                                 ok=ok and ok_flag, duration_ms=dur_ms,
                                 exit_code=int(rc.group(1)) if rc else (0 if ok else 1)))
                if not ok:
                    had_failure = True
                    events.append(mk("tool_failure", stamp, entity_id=entity,
                                     error_class=classify_error(body[:400]),
                                     ok=False, duration_ms=dur_ms))
            elif kind == "assistant":
                if last_tool_entity:
                    claim_n += 1
                    open_claim = last_tool_entity
                    events.append(mk("claim_made", stamp, entity_id=last_tool_entity,
                                     claim_type="assertion_about_artifact",
                                     confidence=0.5))
            elif kind == "user":
                events.append(mk("question_open", stamp,
                                 entity_id="question#{}".format(tool_n + claim_n + 1),
                                 closed_gap=False))
            elif kind in ("end", "ended", "done", "summary"):
                saw_end = True

    if pending_tools:
        # A tool call with no result row: the run died mid-call.
        saw_end = False

    abrupt = bool(pending_tools)
    resolved = (not had_failure) and (not abrupt) and saw_end
    events.append(mk("session_ended", stamp_for(first_ts, path),
                     resolved=resolved, abrupt=abrupt,
                     entity_id=path.parent.name))
    return events


def stamp_for(first_ts, path):
    if not first_ts:
        return now()
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def ingest(paths, transcripts, stdin_text=None):
    if FORCE_ERROR == "ingest":
        raise ModuleError("forced error (STAMP_FORCE_ERROR=ingest)")
    events = load_events(paths, stdin_text=stdin_text)
    for t in transcripts:
        path = Path(t)
        if path.is_dir():
            for sub in sorted(path.rglob("task-*.log")):
                events.extend(transcript_events(sub))
        elif path.exists():
            events.extend(transcript_events(path))
        else:
            raise ModuleError("transcript not found: {}".format(path.name))
    events.sort(key=lambda e: (e["ts"], e["kind"]))
    return events


# ===========================================================================
# MODULE 2 -- honesty corpus
# ===========================================================================
def build_corpus(events):
    """Pair every claim_made with the tool_result that checked it.

    A claim is verified when a successful tool_result lands on the SAME
    entity_id after the claim; contradicted when a failing one does; and
    unverified when no such result ever arrives. UNVERIFIED CLAIMS ARE THE
    MOST VALUABLE ROWS -- asserted and never checked is the honesty signal.
    """
    if FORCE_ERROR == "corpus":
        raise ModuleError("forced error (STAMP_FORCE_ERROR=corpus)")
    results = {}
    claims = []
    for ev in events:
        if ev["kind"] == "tool_result":
            results.setdefault(ev.get("entity_id"), []).append(ev)
        elif ev["kind"] == "claim_made":
            claims.append(ev)

    rows = []
    for claim in claims:
        entity = claim.get("entity_id")
        claim_dt = parse_ts(claim["ts"])
        verdict = None
        verify_ts = None
        for res in results.get(entity, []):
            res_dt = parse_ts(res["ts"])
            if res_dt < claim_dt:
                continue
            verdict = "verified" if res.get("ok") else "contradicted"
            verify_ts = res["ts"]
            break
        outcome = verdict if verdict is not None else "unverified"
        if verdict is None:
            verify_ts = None
        latency = round((parse_ts(verify_ts) - claim_dt).total_seconds(), 3) \
            if verify_ts else None
        rows.append({
            "entity_id": entity,
            "claim_type": claim.get("claim_type", "unspecified"),
            "claim_timestamp": claim["ts"],
            "verify_timestamp": verify_ts,
            "outcome": outcome,
            "latency_seconds": latency,
            "confidence": claim.get("confidence"),
        })
    return rows


# ===========================================================================
# MODULE 3 -- absence ledger
# ===========================================================================
def bucket(age_hours):
    if age_hours < 24:
        return "fresh"
    if age_hours <= 72:
        return "aging"
    return "stale"


def build_absence(events):
    if FORCE_ERROR == "absence":
        raise ModuleError("forced error (STAMP_FORCE_ERROR=absence)")
    now_utc = datetime.now(timezone.utc)
    latest = max((e["ts"] for e in events), default=None)
    reference = parse_ts(latest) if latest else now_utc
    ref = max(reference, now_utc)

    open_questions, open_findings = {}, {}
    questions_total = questions_closed = 0
    findings_total = findings_closed = 0
    sessions_total = sessions_unresolved = 0
    abrupt = 0
    corrections_given = corrections_applied = 0
    failures = {}

    for ev in events:
        kind = ev["kind"]
        ent = ev.get("entity_id")
        age_h = round(max((ref - parse_ts(ev["ts"])).total_seconds(), 0) / 3600.0, 2)
        if kind == "question_open":
            questions_total += 1
            open_questions[ent] = age_h
        elif kind == "question_closed":
            questions_closed += 1
            open_questions.pop(ent, None)
        elif kind == "finding_raised":
            findings_total += 1
            open_findings[ent] = age_h
        elif kind == "finding_closed":
            findings_closed += 1
            open_findings.pop(ent, None)
        elif kind == "session_ended":
            sessions_total += 1
            if not ev.get("resolved", False):
                sessions_unresolved += 1
            if ev.get("abrupt", False):
                abrupt += 1
        elif kind == "correction_given":
            corrections_given += 1
        elif kind == "correction_applied":
            corrections_applied += 1
        elif kind == "tool_failure":
            cls = ev.get("error_class", "unknown")
            failures[cls] = failures.get(cls, 0) + 1

    staleness = {"fresh": 0, "aging": 0, "stale": 0}
    open_items = []
    for ent, age_h in list(open_questions.items()) + list(open_findings.items()):
        b = bucket(age_h)
        staleness[b] += 1
        open_items.append({"entity_id": ent, "age_hours": age_h, "bucket": b})

    return {
        "questions_total": questions_total,
        "questions_open": len(open_questions),
        "questions_closed": questions_closed,
        "unanswered_ratio": round(len(open_questions) / questions_total, 4)
                            if questions_total else None,
        "findings_total": findings_total,
        "findings_open": len(open_findings),
        "findings_closed": findings_closed,
        "sessions_total": sessions_total,
        "abandonment_rate": round(sessions_unresolved / sessions_total, 4)
                            if sessions_total else None,
        "session_ended_abruptly": abrupt,
        "corrections_given": corrections_given,
        "corrections_applied": corrections_applied,
        # A system that is never corrected has stopped being accompanied.
        # correction_weight is the acted-upon ratio; corrections_ignored is
        # what the human said that never landed.
        "correction_weight": round(corrections_applied / corrections_given, 4)
                             if corrections_given else None,
        "corrections_ignored": max(corrections_given - corrections_applied, 0),
        "tool_failures_by_class": failures,
        "staleness": staleness,
        "open_items": sorted(open_items, key=lambda i: -i["age_hours"])[:50],
    }


# ===========================================================================
# MODULE 5 -- hash chain (defined before the finding layer that uses it)
# ===========================================================================
def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def record_hash(prev: str, record: dict) -> str:
    return hashlib.sha256((prev + canonical(record)).encode("utf-8")).hexdigest()


def load_chain():
    records = []
    if not CHAIN.exists():
        return records
    with CHAIN.open("r", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"__corrupt__": True, "line": lineno})
    return records


def append_chain(records):
    """Append records to the chain, linking each to the current head."""
    if not records:
        return GENESIS, 0
    CHAIN.parent.mkdir(parents=True, exist_ok=True)
    prev = load_state().get("chain_head", GENESIS)
    seq = int(load_state().get("chain_seq", 0) or 0)
    written = 0
    with CHAIN.open("a") as fh:
        for rec in records:
            seq += 1
            h = record_hash(prev, rec)
            fh.write(canonical({"seq": seq, "prev": prev, "record": rec,
                                "hash": h}) + "\n")
            prev = h
            written += 1
    save_state({**load_state(), "chain_head": prev, "chain_seq": seq})
    return prev, written


def verify_chain():
    """Recompute the whole chain. Returns (ok, [problems], head, count)."""
    if FORCE_ERROR == "chain":
        raise ModuleError("forced error (STAMP_FORCE_ERROR=chain)")
    problems = []
    prev = GENESIS
    expected_seq = 1
    count = 0
    for entry in load_chain():
        count += 1
        if entry.get("__corrupt__"):
            problems.append("unparseable chain line {}".format(entry.get("line")))
            prev = GENESIS
            expected_seq += 1
            continue
        rec = entry.get("record")
        if rec is None:
            problems.append("record {} has no payload".format(entry.get("seq")))
            continue
        if entry.get("seq") != expected_seq:
            problems.append("sequence break at {}: expected {} found {}".format(
                count, expected_seq, entry.get("seq")))
            expected_seq = entry.get("seq", expected_seq)
        if entry.get("prev") != prev:
            problems.append("link break at record {}: prev does not match head".format(
                entry.get("seq")))
        recomputed = record_hash(entry.get("prev", ""), rec)
        if recomputed != entry.get("hash"):
            problems.append("hash mismatch at record {}: record was mutated".format(
                entry.get("seq")))
        prev = entry.get("hash", prev)
        expected_seq += 1

    state = load_state()
    head, seq = state.get("chain_head", GENESIS), int(state.get("chain_seq", 0) or 0)
    if count and seq != count:
        problems.append("state head claims {} records, chain file holds {} "
                        "(truncated or appended out of band)".format(seq, count))
    if count and not seq and head != GENESIS:
        problems.append("state head set but chain file empty")
    return (not problems), problems, head, count


# ===========================================================================
# MODULE 4 -- findings + dedup
# ===========================================================================
def corpus_findings(rows):
    out = []
    for r in rows:
        if r["outcome"] == "contradicted":
            out.append(finding(
                "corpus", "claim_contradicted", CRITICAL, str(r["entity_id"]),
                "a tool result on this entity CONTRADICTED a claim the agent "
                "had already made",
                {"claim_type": r["claim_type"], "latency_seconds": r["latency_seconds"],
                 "outcome": r["outcome"]}))
        elif r["outcome"] == "unverified":
            out.append(finding(
                "corpus", "claim_unverified", CRITICAL, str(r["entity_id"]),
                "claim asserted and never checked against any machine result. "
                "This is the honesty signal: nobody noticed it was unchecked.",
                {"claim_type": r["claim_type"], "outcome": r["outcome"]}))
    return out


def absence_findings(ledger):
    out = []
    for item in ledger["open_items"]:
        if item["bucket"] == "stale":
            out.append(finding(
                "absence", "gap_stale", CRITICAL, str(item["entity_id"]),
                "unresolved gap older than 72h ({}h)".format(item["age_hours"]),
                {"age_hours": item["age_hours"], "bucket": item["bucket"]}))
        elif item["bucket"] == "aging":
            out.append(finding(
                "absence", "gap_aging", WARN, str(item["entity_id"]),
                "unresolved gap between 24h and 72h ({}h)".format(item["age_hours"]),
                {"age_hours": item["age_hours"], "bucket": item["bucket"]}))
    ur = ledger["unanswered_ratio"]
    if ur is not None and ur >= 0.5 and ledger["questions_total"] >= 3:
        out.append(finding(
            "absence", "unanswered_ratio_high", CRITICAL, "questions",
            "unanswered_ratio {} over {} question(s)".format(ur, ledger["questions_total"]),
            {"unanswered_ratio": ur, "questions_open": ledger["questions_open"]}))
    elif ur is not None and ur > 0 and ledger["questions_total"] >= 3:
        out.append(finding(
            "absence", "unanswered_ratio_partial", WARN, "questions",
            "unanswered_ratio {} over {} question(s)".format(ur, ledger["questions_total"]),
            {"unanswered_ratio": ur, "questions_open": ledger["questions_open"]}))
    ar = ledger["abandonment_rate"]
    if ar is not None and ar >= 0.5 and ledger["sessions_total"]:
        out.append(finding(
            "absence", "session_abandoned", CRITICAL, "sessions",
            "abandonment_rate {} over {} session(s): ended with resolved=false".format(
                ar, ledger["sessions_total"]),
            {"abandonment_rate": ar, "sessions_total": ledger["sessions_total"]}))
    if ledger["session_ended_abruptly"]:
        out.append(finding(
            "absence", "session_ended_abruptly", WARN, "sessions",
            "{} session(s) ended abruptly (tool call with no result)".format(
                ledger["session_ended_abruptly"]),
            {"session_ended_abruptly": ledger["session_ended_abruptly"]}))
    if ledger["corrections_given"] and ledger["correction_weight"] == 0.0:
        out.append(finding(
            "absence", "corrections_never_applied", CRITICAL, "corrections",
            "{} correction(s) from the human, 0 acted upon: a system that is "
            "never corrected has stopped being accompanied".format(
                ledger["corrections_given"]),
            {"corrections_given": ledger["corrections_given"],
             "corrections_applied": ledger["corrections_applied"],
             "correction_weight": 0.0}))
    elif ledger["corrections_ignored"]:
        out.append(finding(
            "absence", "corrections_ignored", WARN, "corrections",
            "{} of {} correction(s) not acted upon".format(
                ledger["corrections_ignored"], ledger["corrections_given"]),
            {"corrections_ignored": ledger["corrections_ignored"]}))
    for cls, count in sorted(ledger["tool_failures_by_class"].items()):
        out.append(finding(
            "corpus", "tool_failure", WARN, "error_class:{}".format(cls),
            "{} tool failure(s) classified {}. The error STRING is never recorded.".format(
                count, cls),
            {"error_class": cls, "count": count}))
    return out


# -- dedup state (shared with the finding layer) ----------------------------
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


def new_criticals(findings, state):
    """Only NEW CRITICAL fingerprints -- the gate for notify."""
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


def evidence_dir(day=None):
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


def notify(findings):
    if not findings:
        return True
    try:
        sys.path.insert(0, str(REPO))
        import notify as notify_mod
    except Exception as exc:
        print("notify unavailable: {}".format(exc), file=sys.stderr)
        return False
    token, chat = notify_mod.get_token(), notify_mod.get_chat_id()
    if not token or not chat:
        print("notify: no bot token/chat id; skipping send", file=sys.stderr)
        return False
    lines = ["*EVEZ STAMP \\u2014 NEW provenance gap*"]
    for f in findings:
        lines.append("\\u2022 [{}] {}".format(f["check"], f["where"]))
    ok, err = notify_mod.api("sendMessage", {"chat_id": chat,
                                             "text": "\n".join(lines)[:4000],
                                             "parse_mode": "Markdown"})
    if not ok:
        print("notify send failed: {}".format(err), file=sys.stderr)
    return bool(ok)


# ===========================================================================
# orchestration
# ===========================================================================
def run(event_paths=(), transcripts=(), do_notify=False, stdin_text=None):
    findings, errored, records = [], False, []

    # ingest
    try:
        events = ingest(event_paths, transcripts, stdin_text)
        records.append({"module": "ingest", "event_count": len(events),
                        "kinds": sorted({e["kind"] for e in events})})
    except ModuleError as exc:
        events = []
        errored = True
        findings.append(finding("ingest", "module_error", WARN, "ingest",
                                "ingest did not complete: {}".format(exc), errored=True))
    except Exception as exc:
        events = []
        errored = True
        findings.append(finding("ingest", "module_error", WARN, "ingest",
                                "unhandled {} in ingest".format(type(exc).__name__),
                                errored=True))

    # corpus
    corpus = []
    try:
        corpus = build_corpus(events)
        records.append({"module": "corpus", "rows": corpus})
        findings.extend(corpus_findings(corpus))
    except Exception as exc:
        errored = True
        findings.append(finding("corpus", "module_error", WARN, "corpus",
                                "unhandled {} in corpus build".format(type(exc).__name__),
                                errored=True))

    # absence
    ledger = {}
    try:
        ledger = build_absence(events)
        records.append({"module": "absence", "ledger": ledger})
        findings.extend(absence_findings(ledger))
    except Exception as exc:
        errored = True
        findings.append(finding("absence", "module_error", WARN, "absence",
                                "unhandled {} in absence ledger".format(
                                    type(exc).__name__), errored=True))

    if not events:
        findings.append(finding(
            "ingest", "no_events", INFO, "stream",
            "empty event stream: nothing claimed, nothing unresolved, no corpus "
            "rows. Recorded so a silent zero is distinguishable from a clean run.",
            {"event_count": 0}))
    elif not findings:
        findings.append(finding(
            "corpus", "stream_clean", INFO, "stream",
            "{} event(s), {} claim row(s), no unverified claims and no open gaps".format(
                len(events), len(corpus)),
            {"event_count": len(events), "corpus_rows": len(corpus)}))

    state = load_state()
    fresh = new_criticals(findings, state)
    state["last_run"] = now()
    state["event_count"] = len(events)
    save_state(state)

    # hash chain over every record this run produced
    head, appended = append_chain(records)
    path = write_evidence(findings)

    if do_notify and fresh:
        notify(fresh)

    active = [f for f in findings if f["severity"] in ACTIONABLE]
    rc = EXIT_ERROR if errored else (EXIT_FINDINGS if active else EXIT_CLEAN)
    return rc, {
        "events": len(events),
        "corpus_rows": len(corpus),
        "outcomes": {o: sum(1 for r in corpus if r["outcome"] == o)
                     for o in ("verified", "contradicted", "unverified")},
        "absence": {k: v for k, v in (ledger or {}).items() if k != "open_items"},
        "open_gaps": len((ledger or {}).get("open_items", [])),
        "findings": len(findings),
        "critical": sum(1 for f in findings if f["severity"] == CRITICAL),
        "warn": sum(1 for f in findings if f["severity"] == WARN),
        "info": sum(1 for f in findings if f["severity"] == INFO),
        "errored_modules": sorted({f["check"] for f in findings if f["errored"]}),
        "new_critical": len(fresh),
        "chain_records_appended": appended,
        "chain_head": head,
        "evidence": str(path),
        "exit_code": rc,
        "fingerprints": [f["fingerprint"] for f in findings],
    }


def do_verify():
    try:
        ok, problems, head, count = verify_chain()
    except ModuleError as exc:
        print("chain verify did not complete: {}".format(exc), file=sys.stderr)
        return EXIT_ERROR
    summary = {"chain_ok": ok, "records": count, "chain_head": head,
               "problems": problems, "exit_code": 0 if ok else EXIT_FINDINGS}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return EXIT_CLEAN if ok else EXIT_FINDINGS


def main(argv=None):
    ap = argparse.ArgumentParser(description="EVEZ-OS STAMP provenance daemon")
    ap.add_argument("--events", action="append", default=[],
                    help="JSONL event file (repeatable); also read stdin")
    ap.add_argument("--transcript", action="append", default=[],
                    help="Hermes session transcript or directory (repeatable)")
    ap.add_argument("--verify", action="store_true",
                    help="recompute the hash chain; nonzero exit if broken")
    ap.add_argument("--notify", action="store_true",
                    help="Telegram-send only NEW criticals (deduped by fingerprint)")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args(argv)

    if args.verify:
        return do_verify()

    transcripts = args.transcript or ([str(TRANSCRIPTS)] if TRANSCRIPTS.exists() else [])
    stdin_text = None
    if not args.events and not args.transcript and not sys.stdin.isatty():
        stdin_text = sys.stdin.read()
    rc, summary = run(args.events, transcripts, args.notify, stdin_text)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("events={} corpus_rows={} verified={} contradicted={} unverified={} "
              "findings={} critical={} warn={} info={} new_critical={} "
              "chain+={} rc={} -> {}".format(
                  summary["events"], summary["corpus_rows"],
                  summary["outcomes"]["verified"], summary["outcomes"]["contradicted"],
                  summary["outcomes"]["unverified"], summary["findings"],
                  summary["critical"], summary["warn"], summary["info"],
                  summary["new_critical"], summary["chain_records_appended"],
                  rc, summary["evidence"]))
        for f in summary["fingerprints"]:
            print("  fp=" + f)
        if summary["errored_modules"]:
            print("  ERRORED MODULES: " + ", ".join(summary["errored_modules"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
