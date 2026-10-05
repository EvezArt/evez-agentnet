#!/usr/bin/env python3
"""EVEZ cognition delta ingest authority — the interoperability edge.

All nodes (local or remote, via the NATS subject evez.cognition.delta)
publish proposed state transitions; THIS process is the only writer to
the shared per-day ledger. It enforces, in one place:

  1. The anti-collapse ladder (via cognition_deltas.validate_transition).
  2. Frontier + falsifier presence (via validate_frontier).
  3. SUBJECT-STATE CONTINUITY: state_from must equal the subject's
     CURRENT state as recorded in the shared ledger. A remote node
     cannot launder a promotion by claiming a false state_from.
  4. Server-side monotonic timestamps: nodes with skewed clocks cannot
     regress the chain's time order (their client_ts is preserved as
     provenance).
  5. Every append is acked (hash+seq) or nacked (invariant name) via
     NATS request/reply, so the publishing node learns its fate.

Modes:
  --serve            run the ingest loop forever (systemd)
  --publish FILE     publish a JSON delta request, print ack/nack
  --verify [PATH]    verify a ledger (default: today's)
"""

import argparse
import fcntl
import json
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cognition_deltas import DeltaLedger, DeltaError, validate_frontier, validate_transition
from nats_client import NatsClient, NatsError

SUBJECT_IN = "evez.cognition.delta"
SUBJECT_STREAM = "evez.cognition.delta.appended"
REQUIRED = ("node", "model", "aemdas_stage", "subject", "state_from", "state_to",
            "response", "context", "frontier")
OPTIONAL = ("evidence", "contradiction", "result", "client_ts", "next_frontier")


def today_ledger_path(base: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return base / "evidence" / day / "cognition_deltas.jsonl"


def subject_states(ledger_path: Path) -> dict:
    """Current state per subject, reconstructed from the ledger."""
    states = {}
    seen = set()
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # No ledger yet: every subject is at UNKNOWN.
        return states
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or "hash" not in row:
            continue
        subj = row.get("subject")
        if subj and subj not in seen:
            seen.add(subj)
        states[subj] = row.get("state_to")
    return states


class IngestAuthority:
    def __init__(self, base: Path):
        self.base = base
        self.ledger_path = today_ledger_path(base)
        self.ledger = DeltaLedger(self.ledger_path)
        self.lock_path = self.ledger_path.with_suffix(".lock")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fh = None
        self.stats = {"appended": 0, "rejected": 0}

    def handle(self, payload: bytes) -> dict:
        try:
            req = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.stats["rejected"] += 1
            return {"ok": False, "invariant": "unparseable-request", "detail": str(exc)}
        if not isinstance(req, dict):
            self.stats["rejected"] += 1
            return {"ok": False, "invariant": "unparseable-request", "detail": "not an object"}

        for field in REQUIRED:
            if field not in req:
                self.stats["rejected"] += 1
                return {"ok": False, "invariant": "field-missing", "detail": field}

        with self._locked():
            # Roll over at UTC midnight: the shared ledger is per-day.
            fresh = today_ledger_path(self.base)
            if fresh != self.ledger_path:
                self.ledger_path = fresh
                self.ledger = DeltaLedger(self.ledger_path)

            current = subject_states(self.ledger_path)
            subj = req["subject"]
            state_from = req["state_from"]
            if subj in current and current[subj] != state_from:
                self.stats["rejected"] += 1
                return {
                    "ok": False,
                    "invariant": "subject-state-continuity",
                    "detail": f"laundering rejected: subject '{subj}' is at {current[subj]}, not {state_from}",
                }
            if subj not in current and state_from not in ("UNKNOWN", "LOCKED"):
                self.stats["rejected"] += 1
                return {
                    "ok": False,
                    "invariant": "subject-state-continuity",
                    "detail": f"new subject '{subj}' must start at UNKNOWN or LOCKED, not {state_from}",
                }

            client_ts = req.get("client_ts", "")
            try:
                ts = self._server_ts()
                delta = self.ledger.append(
                    node=req["node"], model=req["model"],
                    aemdas_stage=req["aemdas_stage"], subject=subj,
                    state_from=state_from, state_to=req["state_to"],
                    response=req["response"], context=req.get("context") or {},
                    frontier=req["frontier"],
                    next_frontier=req.get("next_frontier", ""),
                    result=req.get("result"),
                    evidence=req.get("evidence"),
                    contradiction=req.get("contradiction", ""),
                    ts=ts,
                )
            except DeltaError as exc:
                self.stats["rejected"] += 1
                return {"ok": False, "invariant": exc.invariant, "detail": str(exc)}

        self.stats["appended"] += 1
        return {
            "ok": True, "hash": delta["hash"], "seq": delta["seq"],
            "server_ts": delta["ts"], "client_ts_provenance": client_ts,
            "subject_state_now": req["state_to"],
        }

    def _locked(self):
        class _Ctx:
            def __init__(outer, fh):
                outer.fh = fh
            def __enter__(outer):
                fcntl.flock(outer.fh, fcntl.LOCK_EX)
            def __exit__(outer, *a):
                fcntl.flock(outer.fh, fcntl.LOCK_UN)
        if self._lock_fh is None:
            self._lock_fh = open(self.lock_path, "a+")
        return _Ctx(self._lock_fh)

    def _server_ts(self) -> str:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        tail = self.ledger._tail()
        if tail and tail.get("ts", "") >= now:
            # monotonic: never regress, bump a second if we must.
            base = datetime.fromisoformat(tail["ts"])
            now = (base + __import__("datetime").timedelta(seconds=1)).isoformat(timespec="seconds")
        return now


def serve(base: Path, host="127.0.0.1", port=4222):
    auth = IngestAuthority(base)
    nc = NatsClient(host=host, port=port, name="evez-delta-ingest")
    nc.sub(SUBJECT_IN, 1)
    print(f"[ingest] subscribed {SUBJECT_IN} on {host}:{port}; ledger {auth.ledger_path}", flush=True)
    stop = threading.Event()
    def _sig(_s, _f):
        stop.set()
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    while not stop.is_set():
        try:
            msg = nc.next_msg(timeout=5.0)
        except (NatsError, OSError) as exc:
            print(f"[ingest] transport error: {exc}; exiting", flush=True)
            sys.exit(1)
        if msg is None:
            print(f"[ingest] alive appended={auth.stats['appended']} rejected={auth.stats['rejected']}", flush=True)
            continue
        subject, reply, payload = msg
        result = auth.handle(payload)
        out = json.dumps(result).encode()
        if reply:
            nc.publish(reply, out)
        if result.get("ok"):
            nc.publish(SUBJECT_STREAM, out)
        print(f"[ingest] {'APPEND' if result.get('ok') else 'REJECT'} "
              f"{result.get('hash', '')[:16] if result.get('ok') else result.get('invariant')}", flush=True)


def publish(base: Path, spec_file: Path, host="127.0.0.1", port=4222):
    spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
    nc = NatsClient(host=host, port=port, name=f"evez-delta-pub-{spec.get('node', 'anon')}")
    ack = nc.request(SUBJECT_IN, json.dumps(spec).encode(), timeout=15.0)
    print(json.dumps(ack, indent=2))
    nc.close()
    return 0 if ack.get("ok") else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["serve", "publish", "verify"])
    ap.add_argument("path", nargs="?", help="spec json (publish) or ledger path (verify)")
    ap.add_argument("--base", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    base = Path(args.base)
    if args.mode == "serve":
        serve(base)
    elif args.mode == "publish":
        sys.exit(publish(base, Path(args.path)))
    else:
        ledger = DeltaLedger(Path(args.path) if args.path else today_ledger_path(base))
        ok, errors, count = ledger.verify()
        print(json.dumps({"ok": ok, "records": count, "errors": errors}, indent=2))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
