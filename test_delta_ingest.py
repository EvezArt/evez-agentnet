#!/usr/bin/env python3
"""Multi-node forest tests: ingest authority, NATS transport, laundering rejection.

Falsifiers:
  - a node with a SKEWED CLOCK appends and the chain still verifies
    (server-side timestamps win; client_ts kept as provenance);
  - a second node attempts to launder a promotion (claims state_from
    the shared ledger never recorded) -> subject-state-continuity nack;
  - a legal cross-node promotion through the real NATS transport;
  - the forest verifier catches a promotion that only the per-file
    chain check would miss.
Runs against the LIVE nats-server on 127.0.0.1:4222.
"""

import json
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import delta_ingest
import forest_verify
from cognition_deltas import DeltaLedger


def _req(node="gcp-west", subject="mesh-substrate", state_from="UNKNOWN",
         state_to="PROPOSED", client_ts=None, **extra):
    r = {
        "node": node, "model": "GLM-5.1-FP8", "aemdas_stage": "EXTRACT",
        "subject": subject, "state_from": state_from, "state_to": state_to,
        "response": "r", "context": {"question_id": "Q1", "target_id": "t"},
        "frontier": {
            "statement": "s", "why": "w", "required": "r",
            "test": "flip one byte; the chain must fail naming the line",
            "next": "n", "loot": "l",
        },
        "client_ts": client_ts or "2020-01-01T00:00:00+00:00",
    }
    r.update(extra)
    return r


def _serve_thread(base):
    auth = delta_ingest.IngestAuthority(base)
    stop = {"flag": False}
    def run():
        from nats_client import NatsClient
        nc = NatsClient(name="test-ingest")
        nc.sub(delta_ingest.SUBJECT_IN, 1)
        while not stop["flag"]:
            msg = nc.next_msg(timeout=0.4)
            if msg is None:
                continue
            _s, reply, payload = msg
            out = auth.handle(payload)
            if reply:
                nc.publish(reply, json.dumps(out).encode())
        nc.close()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.3)
    return t, stop


def _stop_serve(stop, thread=None, timeout=5.0):
    """Stop the ingest server and WAIT for it to exit.

    Without the join, the dying thread can still be parked in next_msg for up
    to one poll timeout; it then swallows the NEXT test's publish and dies
    on its deleted tempdir, polluting stderr (and racing the new server's
    reply into the wrong inbox).
    """
    stop["flag"] = True
    if thread is not None:
        thread.join(timeout=timeout)
        assert not thread.is_alive(), "ingest serve thread did not stop"


class _Pub:
    """Direct request to the test ingest thread over real NATS."""
    def __init__(self):
        from nats_client import NatsClient
        self.nc = NatsClient(name="test-pub")

    def send(self, req):
        return self.nc.request(delta_ingest.SUBJECT_IN, json.dumps(req).encode(), timeout=10)


def test_skewed_clock_node_appends_and_chain_verifies():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        t, stop = _serve_thread(base)
        try:
            pub = _Pub()
            # clock is 5 YEARS in the past
            ack = pub.send(_req(client_ts="2021-01-01T00:00:00+00:00"))
            assert ack["ok"], ack
            assert ack["client_ts_provenance"] == "2021-01-01T00:00:00+00:00"
            # clock is 5 years in the FUTURE
            ack2 = pub.send(_req(subject="future-node", client_ts="2031-01-01T00:00:00+00:00",
                                 node="gcp-knot"))
            assert ack2["ok"], ack2
            ok, errors, n = DeltaLedger(delta_ingest.today_ledger_path(base)).verify()
            assert ok, errors
            assert n == 2, n
        finally:
            _stop_serve(stop, t)


def test_cross_node_laundering_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        t, stop = _serve_thread(base)
        try:
            pub = _Pub()
            a = pub.send(_req(node="gcp-west", subject="shared-subject"))
            assert a["ok"], a
            # node B never saw node A's PROPOSED; claims it was already TESTABLE->SUPPORTED
            b = pub.send(_req(node="gcp-knot", subject="shared-subject",
                              state_from="TESTABLE", state_to="SUPPORTED",
                              evidence={"measurements": [{"rc": 0}], "replications": []}))
            assert not b["ok"], b
            assert b["invariant"] == "subject-state-continuity", b
            # the shared ledger still has the subject at PROPOSED
            states = delta_ingest.subject_states(delta_ingest.today_ledger_path(base))
            assert states["shared-subject"] == "PROPOSED", states
        finally:
            _stop_serve(stop, t)


def test_legal_cross_node_promotion_via_nats():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        t, stop = _serve_thread(base)
        try:
            pub = _Pub()
            r1 = pub.send(_req(node="vultr", subject="interop", state_from="UNKNOWN", state_to="PROPOSED"))
            assert r1["ok"], r1
            r2 = pub.send(_req(node="gcp-west", subject="interop", state_from="PROPOSED", state_to="TESTABLE"))
            assert r2["ok"], r2
            r3 = pub.send(_req(node="gcp-power", subject="interop", state_from="TESTABLE", state_to="SUPPORTED",
                               evidence={"measurements": [{"exec": "bench", "rc": 0}], "replications": []}))
            assert r3["ok"], r3
            # replication must come from a DIFFERENT node to earn VERIFIED
            r4 = pub.send(_req(node="gcp-openclaw", subject="interop", state_from="SUPPORTED", state_to="VERIFIED",
                               evidence={"measurements": [{"exec": "bench", "rc": 0}],
                                         "replications": [{"exec": "bench", "node": "gcp-openclaw", "rc": 0}]}))
            assert r4["ok"], r4
            # forest-level: all four transitions verify, continuity holds, replication present
            rep = forest_verify.verify_forest(base)
            assert rep["ok"], rep["errors"]
            assert rep["subjects"]["interop"] == "VERIFIED", rep["subjects"]
        finally:
            _stop_serve(stop, t)


def test_forest_verifier_catches_cross_file_laundering():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "evidence" / "2026-10-04").mkdir(parents=True)
        (base / "evidence" / "2026-10-05").mkdir(parents=True)
        day1 = base / "evidence" / "2026-10-04" / "cognition_deltas.jsonl"
        day2 = base / "evidence" / "2026-10-05" / "cognition_deltas.jsonl"
        led1 = DeltaLedger(day1)
        led2 = DeltaLedger(day2)
        f = {"statement": "s", "why": "w", "required": "r",
             "test": "flip one byte; the chain must fail naming the line",
             "next": "n", "loot": "l"}
        led1.append(node="a", model="m", aemdas_stage="ASSERT", subject="x",
                    state_from="UNKNOWN", state_to="PROPOSED",
                    response="r", context={}, frontier=f,
                    ts="2026-10-04T00:00:00+00:00")
        # day-2 ledger NEVER saw day-1's tail: subject x claims TESTABLE->SUPPORTED.
        # Per-record the transition is legal; only the FOREST sees that x was
        # never at TESTABLE (it sat at PROPOSED in day-1) and catches the
        # laundering. (The old TESTABLE->VERIFIED claim is now rejected by the
        # per-record ladder itself, which would make this a non-test.)
        led2.append(node="b", model="m", aemdas_stage="DEDUCE", subject="x",
                     state_from="TESTABLE", state_to="SUPPORTED",
                     response="r", context={}, frontier=f,
                     evidence={"measurements": [], "replications": [{"n": 1}]},
                     ts="2026-10-05T00:00:00+00:00")
        # each chain alone verifies; the FOREST catches the laundering
        rep = forest_verify.verify_forest(base)
        assert not rep["ok"], "forest blessed cross-file laundering"
        assert any("continuity broken" in e for e in rep["errors"]), rep["errors"]


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"OK {len(tests)} tests")


if __name__ == "__main__":
    main()
