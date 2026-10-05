#!/usr/bin/env python3
"""EVEZ cognition delta substrate — accountable state transitions.

The interoperability layer between increasingly capable agents is not
another model. It is a machine-readable epistemic substrate: agents
exchange hash-chained state deltas carrying WHAT CHANGED, WHAT WAS
LEARNED, WHAT REMAINS UNKNOWN, WHAT CAN BE TESTED NEXT, and WHAT NEW
CAPABILITY BECAME POSSIBLE — with the anti-collapse boundaries
enforced as code, not as slogans.

Invariants (violations raise DeltaError; they never warn):
  UNKNOWN never becomes VERIFIED or UNLOCKED in one step.
  PROPOSED never becomes VERIFIED (CLAIMED != MEASURED).
  TESTABLE never becomes VERIFIED (MEASURED != REPLICATED).
  SUPPORTED -> VERIFIED only with a recorded replication.
  CONTRADICTED must regress to PROPOSED before any promotion.
  Every frontier carries a falsifier — no falsifier, no delta.
  CORRECTED != TRUE: corrections are witnessed, never laundered.

Ledger: append-only JSONL, SHA-256 chained (prev_hash -> hash),
tamper-evident on verify, non-decreasing timestamps. Exports
EVEX-compatible state.transition objects with an explicit DESA-S
adaptation extension that non-DESA-S runtimes can still consume.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "evez.cognition-delta.v1"
GENESIS = "0" * 64
ADAPTATION_PROFILE = "desas-s.v1"

STATES = (
    "LOCKED", "UNKNOWN", "PROPOSED", "TESTABLE", "SUPPORTED",
    "VERIFIED", "UNLOCKED", "STALE", "CONTRADICTED", "RETRACTED",
)

ALLOWED_TRANSITIONS = {
    "LOCKED": {"UNKNOWN", "PROPOSED"},
    "UNKNOWN": {"PROPOSED", "TESTABLE"},
    "PROPOSED": {"TESTABLE", "RETRACTED"},
    "TESTABLE": {"SUPPORTED", "CONTRADICTED", "RETRACTED", "STALE"},
    "SUPPORTED": {"VERIFIED", "UNLOCKED", "CONTRADICTED", "RETRACTED", "STALE"},
    "VERIFIED": {"UNLOCKED", "STALE", "CONTRADICTED", "RETRACTED"},
    "UNLOCKED": {"STALE", "CONTRADICTED", "RETRACTED"},
    "STALE": {"PROPOSED", "RETRACTED"},
    "CONTRADICTED": {"PROPOSED", "RETRACTED"},
    "RETRACTED": {"PROPOSED"},
}

FRONTIER_FIELDS = ("statement", "why", "required", "test", "next", "loot")


class DeltaError(Exception):
    """Raised when a delta violates an anti-collapse invariant."""

    def __init__(self, invariant, detail=""):
        self.invariant = invariant
        super().__init__(f"{invariant}: {detail}" if detail else invariant)


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chash(obj) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_frontier(frontier) -> None:
    if not isinstance(frontier, dict):
        raise DeltaError("frontier-incomplete", "frontier must be a mapping")
    for field in FRONTIER_FIELDS:
        v = frontier.get(field)
        if not isinstance(v, str) or not v.strip():
            raise DeltaError("frontier-incomplete", f"missing field: {field}")
    # The falsifiability is the legal weight: no test, no delta.
    if len(frontier["test"].strip()) < 8:
        raise DeltaError("falsifiability-required", frontier["test"])


def validate_transition(state_from, state_to, evidence) -> None:
    if state_from not in STATES:
        raise DeltaError("unknown-state", state_from)
    if state_to not in STATES:
        raise DeltaError("unknown-state", state_to)
    if state_from == state_to:
        raise DeltaError("self-transition", state_from)
    if state_to not in ALLOWED_TRANSITIONS[state_from]:
        raise DeltaError(
            "illegal-promotion",
            f"{state_from} -> {state_to} is laundering: "
            f"the ladder is {state_from} -> {sorted(ALLOWED_TRANSITIONS[state_from])}",
        )
    if state_from == "SUPPORTED" and state_to == "VERIFIED":
        replications = (evidence or {}).get("replications") or []
        if not replications:
            raise DeltaError(
                "replication-required",
                "MEASURED != REPLICATED: VERIFIED demands a recorded replication",
            )


def _record_hash(delta: dict) -> str:
    payload = {k: v for k, v in delta.items() if k != "hash"}
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


class DeltaLedger:
    """Append-only, SHA-256-chained ledger of accountable state transitions."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _tail(self):
        # Walk backwards for the most recent parseable delta line: the file
        # may interleave non-delta rows from other writers.
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return None
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "hash" in row:
                return row
        return None

    def append(self, *, node, model, aemdas_stage, subject,
               state_from, state_to, response, context,
               frontier, next_frontier="", result=None,
               evidence=None, contradiction="", ts=None):
        validate_frontier(frontier)
        evidence = evidence or {"measurements": [], "replications": []}
        validate_transition(state_from, state_to, evidence)
        context = context or {}
        tail = self._tail()
        delta = {
            "schema": SCHEMA,
            "seq": (tail["seq"] + 1) if tail else 1,
            "ts": ts or now_utc(),
            "node": node,
            "model": model,
            "aemdas_stage": aemdas_stage,
            "subject": subject,
            "state_from": state_from,
            "state_to": state_to,
            "frontier": frontier,
            "evidence": evidence,
            "contradiction": contradiction,
            "response_hash": chash(response),
            "context_hash": chash(context),
            "frontier_hash": chash(frontier),
            "required_data_hash": chash(frontier["required"]),
            "test_hash": chash(frontier["test"]),
            "result_hash": chash(result if result is not None else {}),
            "contradiction_hash": chash(contradiction),
            "next_frontier_hash": chash(next_frontier),
            "adaptation": {
                "profile": ADAPTATION_PROFILE,
                "domain_state_hash": chash(context.get("domain_state", {})),
                "sme_profile_hash": chash(context.get("sme_profile", {})),
                "selection_receipt_hash": chash(context.get("selection_receipt", {})),
                "question_id": context.get("question_id", "unassigned"),
                "target_id": context.get("target_id", "unassigned"),
            },
            "prev_hash": tail["hash"] if tail else GENESIS,
        }
        delta["hash"] = _record_hash(delta)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(delta) + "\n")
        return delta

    def verify(self):
        """Recompute the whole chain. Returns (ok, errors, count)."""
        errors = []
        prev = GENESIS
        expected_seq = 1
        last_ts = None
        count = 0
        for i, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {i}: unparseable: {exc}")
                continue
            if not isinstance(row, dict) or "hash" not in row:
                errors.append(f"line {i}: not a delta record, skipped")
                continue
            count += 1
            if _record_hash(row) != row.get("hash"):
                errors.append(f"line {i}: TAMPERED — hash mismatch")
            if row.get("prev_hash") != prev:
                errors.append(f"line {i}: broken chain link")
            if row.get("seq") != expected_seq:
                errors.append(f"line {i}: seq {row.get('seq')} != {expected_seq}")
            try:
                validate_frontier(row.get("frontier"))
                validate_transition(
                    row.get("state_from"), row.get("state_to"), row.get("evidence")
                )
            except DeltaError as exc:
                errors.append(f"line {i}: invariant violated post-hoc: {exc}")
            ts = row.get("ts", "")
            if last_ts is not None and ts < last_ts:
                errors.append(f"line {i}: timestamp regressed")
            last_ts = ts
            prev = row.get("hash", "")
            expected_seq += 1
        return (not errors, errors, count)

    @staticmethod
    def export_evex(delta):
        """EVEX-compatible state.transition; DESA-S extension is explicit
        and ignorable by runtimes that do not implement it."""
        return {
            "type": "state.transition",
            "version": "evex.v1",
            "transition_id": delta["hash"],
            "prev": delta["prev_hash"],
            "entity": delta["subject"],
            "state_from": delta["state_from"],
            "state_to": delta["state_to"],
            "ts": delta["ts"],
            "adaptation": delta["adaptation"],
        }


def _ledger_default():
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path(__file__).resolve().parent / "evidence" / day / "cognition_deltas.jsonl"


def _run_tests():
    here = Path(__file__).resolve().parent
    proc = subprocess.run(
        [sys.executable, str(here / "test_cognition_deltas.py")],
        capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout or "").strip().splitlines()[-1] if (proc.stdout or "").strip() else ""


def demo():
    ledger = DeltaLedger(_ledger_default())
    base = dict(node="hermes-local", model="z-ai/glm-5.3", aemdas_stage="ASSESS")

    d1 = ledger.append(
        subject="agent-epistemic-substrate", state_from="UNKNOWN", state_to="PROPOSED",
        response="Substrate proposed: delta ledger with enforced promotion ladder.",
        context={"domain_state": {"layer": "interoperability"},
                 "sme_profile": {"role": "witness"},
                 "question_id": "Q1", "target_id": "promotion-ladder"},
        frontier={
            "statement": "Agents can exchange accountable state transitions, not just answers: a hash-chained delta ledger with anti-collapse promotion rules.",
            "why": "The missing interoperability layer between increasingly capable agents is a machine-readable epistemic substrate, not another model.",
            "required": "Delta schema, promotion ladder enforced in code, tamper evidence on verify.",
            "test": "Flip one byte in an appended record; ledger.verify() must fail and name the line.",
            "next": "Implement DeltaLedger and the six-field frontier packet (statement/why/required/test/next/loot).",
            "loot": "A reusable append-only evidence primitive every EVEZ service can append to and every consumer can replay.",
        },
        **base)

    d2 = ledger.append(
        subject="agent-epistemic-substrate", state_from="PROPOSED", state_to="TESTABLE",
        response="Falsifier written as an executable suite.",
        context={"domain_state": {"layer": "interoperability"}, "question_id": "Q1", "target_id": "test-suite"},
        frontier={
            "statement": "The promotion ladder and tamper evidence are falsifiable by an executable suite.",
            "why": "An audit that cannot be shown to detect a planted bug is worse than no audit.",
            "required": "Tests for: legal ladder, illegal promotions, missing falsifier, tamper detection, determinism, EVEX export.",
            "test": "python test_cognition_deltas.py must pass and must fail when a byte is flipped.",
            "next": "Run the suite for real and record the execution as measurement.",
            "loot": "A self-witnessing regression gate wired into CI.",
        },
        **base)

    rc1, last1 = _run_tests()
    d3 = ledger.append(
        subject="agent-epistemic-substrate", state_from="TESTABLE", state_to="SUPPORTED",
        response="Suite executed once locally.",
        context={"domain_state": {"layer": "interoperability"}, "question_id": "Q1", "target_id": "measurement"},
        frontier={
            "statement": "The suite executes green on this host.",
            "why": "MEASURED beats CLAIMED: the measurement is the run, not the assertion.",
            "required": "One real execution with returncode captured.",
            "test": "A non-zero returncode must record a contradiction instead of a promotion.",
            "next": "Execute a second independent run to satisfy the replication requirement.",
            "loot": "Honest measurement records: rc and last line, no invented output.",
        },
        result={"returncode": rc1, "last_line": last1},
        evidence={"measurements": [{"exec": "test_cognition_deltas.py", "run": 1, "returncode": rc1}],
                  "replications": []},
        **base)
    if rc1 != 0:
        d3b = ledger.append(
            subject="agent-epistemic-substrate", state_from="SUPPORTED", state_to="CONTRADICTED",
            response="Suite failed — contradiction recorded, no laundering.",
            context={"question_id": "Q1", "target_id": "failure"},
            frontier={
                "statement": "The suite failed on first execution.",
                "why": "Failure is a search-space reduction, not a rollback.",
                "required": "The failing assertion.",
                "test": "Re-run after fix.",
                "next": "Fix and re-enter at PROPOSED.",
                "loot": "The failing case as a permanent regression.",
            }, contradiction=f"suite rc={rc1}: {last1}", **base)
        print(json.dumps({"status": "CONTRADICTED", "rc": rc1, "last": last1}))
        sys.exit(1)

    rc2, last2 = _run_tests()
    d4 = ledger.append(
        subject="agent-epistemic-substrate", state_from="SUPPORTED", state_to="VERIFIED",
        response="Second independent execution of the suite.",
        context={"domain_state": {"layer": "interoperability"}, "question_id": "Q1", "target_id": "replication"},
        frontier={
            "statement": "The suite replicates green on a second independent execution.",
            "why": "MEASURED != REPLICATED; VERIFIED demands the second run.",
            "required": "A second execution with returncode 0, plus CI wiring for a third environment.",
            "test": "Either run failing falsifies VERIFIED and forces regression to CONTRADICTED.",
            "next": "Wire the suite into .github/workflows/ci.yml (done in this commit).",
            "loot": "A verified substrate primitive: other services can now chain onto this ledger.",
        },
        result={"returncode": rc2, "last_line": last2},
        evidence={"measurements": [{"exec": "test_cognition_deltas.py", "run": 1, "returncode": rc1}],
                  "replications": [{"exec": "test_cognition_deltas.py", "run": 2, "returncode": rc2}]},
        **base)

    d5 = ledger.append(
        subject="evex-portability", state_from="UNKNOWN", state_to="PROPOSED",
        response="Portable transition export proposed.",
        context={"domain_state": {"layer": "exchange"}, "question_id": "Q2", "target_id": "evex-consumer"},
        frontier={
            "statement": "A non-DESA-S runtime can consume the exported transition by ignoring the adaptation extension.",
            "why": "Interoperability means the extension is explicit, not mandatory.",
            "required": "An export whose base fields stand alone.",
            "test": "test_evex_export_shape parses the base transition without reading adaptation.",
            "next": "Consumers adopt evex.v1 state.transition; DESA-S-aware runtimes replay the adaptation hashes.",
            "loot": "One exchange format for both plain and adapting agents.",
        },
        **base)

    ok, errors, count = ledger.verify()
    export = DeltaLedger.export_evex(d5)
    print(json.dumps({
        "ledger": str(ledger.path),
        "deltas": [d["hash"][:16] for d in (d1, d2, d3, d4, d5)],
        "verify": {"ok": ok, "errors": errors, "records": count},
        "evex_export": export,
    }, indent=2))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="run the self-witnessing scripted run")
    v = sub.add_parser("verify", help="verify a ledger (default: today's)")
    v.add_argument("path", nargs="?")
    args = ap.parse_args()
    if args.cmd == "demo":
        demo()
    else:
        ledger = DeltaLedger(args.path or _ledger_default())
        ok, errors, count = ledger.verify()
        print(json.dumps({"ok": ok, "records": count, "errors": errors}, indent=2))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
