#!/usr/bin/env python3
"""Anti-collapse tests for the cognition delta substrate.

Every test is a falsifier: if the ladder can be laundered, the falsifier
fails. The suite must be wired into CI (it is — see ci.yml).
"""

import json
import tempfile
from pathlib import Path

import cognition_deltas as cd


def _ledger(tmp):
    return cd.DeltaLedger(Path(tmp) / "cognition_deltas.jsonl")


def _frontier(test="flip one byte in a record; verify must fail naming the line"):
    return {
        "statement": "s", "why": "w", "required": "r",
        "test": test, "next": "n", "loot": "l",
    }


def _append(ledger, **kw):
    base = dict(node="t", model="t", aemdas_stage="ASSERT",
                subject="s", response="r", context={},
                frontier=_frontier(), next_frontier="", result={},
                evidence=None, contradiction="", ts="2026-10-05T00:00:00+00:00")
    base.update(kw)
    return ledger.append(**base)


def test_valid_ladder():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        _append(led, state_from="UNKNOWN", state_to="PROPOSED")
        _append(led, state_from="PROPOSED", state_to="TESTABLE")
        _append(led, state_from="TESTABLE", state_to="SUPPORTED",
                evidence={"measurements": [{"rc": 0}], "replications": []})
        _append(led, state_from="SUPPORTED", state_to="VERIFIED",
                evidence={"measurements": [{"rc": 0}],
                          "replications": [{"rc": 0}]})
        _append(led, state_from="VERIFIED", state_to="UNLOCKED")
        ok, errors, n = led.verify()
        assert ok, errors
        assert n == 5, n


def test_unknown_to_verified_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        try:
            _append(led, state_from="UNKNOWN", state_to="VERIFIED")
        except cd.DeltaError as exc:
            assert exc.invariant == "illegal-promotion", exc.invariant
        else:
            raise AssertionError("UNKNOWN->VERIFIED laundered through")


def test_proposed_to_verified_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        _append(led, state_from="UNKNOWN", state_to="PROPOSED")
        try:
            _append(led, state_from="PROPOSED", state_to="VERIFIED",
                    evidence={"measurements": [{"rc": 0}], "replications": [{"rc": 0}]})
        except cd.DeltaError as exc:
            assert exc.invariant == "illegal-promotion", exc.invariant
        else:
            raise AssertionError("PROPOSED->VERIFIED laundered through")


def test_verified_requires_replication():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        _append(led, state_from="TESTABLE", state_to="SUPPORTED",
                evidence={"measurements": [{"rc": 0}], "replications": []})
        try:
            _append(led, state_from="SUPPORTED", state_to="VERIFIED",
                    evidence={"measurements": [{"rc": 0}], "replications": []})
        except cd.DeltaError as exc:
            assert exc.invariant == "replication-required", exc.invariant
        else:
            raise AssertionError("MEASURED promoted to VERIFIED without REPLICATED")


def test_contradicted_cannot_jump_to_verified():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        _append(led, state_from="TESTABLE", state_to="CONTRADICTED",
                contradiction="measured failure")
        try:
            _append(led, state_from="CONTRADICTED", state_to="VERIFIED",
                    evidence={"measurements": [], "replications": [{"x": 1}]})
        except cd.DeltaError as exc:
            assert exc.invariant == "illegal-promotion", exc.invariant
        else:
            raise AssertionError("CONTRADICTED->VERIFIED laundered through")


def test_missing_falsifier_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        for bad in ({**_frontier(), "test": ""}, {**_frontier(), "test": "short"}):
            try:
                led.append(node="t", model="t", aemdas_stage="ASSERT", subject="s",
                           state_from="UNKNOWN", state_to="PROPOSED",
                           response="r", context={}, frontier=bad)
            except cd.DeltaError as exc:
                assert exc.invariant in ("falsifiability-required", "frontier-incomplete"), exc.invariant
            else:
                raise AssertionError("delta without falsifier accepted")


def test_tamper_detection():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        _append(led, state_from="UNKNOWN", state_to="PROPOSED")
        _append(led, state_from="PROPOSED", state_to="TESTABLE")
        ok, _, _ = led.verify()
        assert ok
        lines = led.path.read_text().splitlines()
        row = json.loads(lines[0])
        row["frontier"]["statement"] = "TAMPERED PAYLOAD"
        lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
        led.path.write_text("\n".join(lines) + "\n")
        ok, errors, _ = led.verify()
        assert not ok, "tampered ledger verified clean"
        assert any("TAMPERED" in e for e in errors), errors


def test_smuggled_promotion_in_file_rejected_on_verify():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        d = _append(led, state_from="UNKNOWN", state_to="PROPOSED")
        # Forge a second record by hand with an illegal promotion, rehash it
        # so only the transition check can catch it.
        forged = dict(d)
        forged.update(seq=2, state_from="UNKNOWN", state_to="VERIFIED",
                      prev_hash=d["hash"], ts=d["ts"])
        forged["hash"] = cd._record_hash(forged)
        with led.path.open("a") as fh:
            fh.write(cd.canonical(forged) + "\n")
        ok, errors, _ = led.verify()
        assert not ok, "verify blessed a hand-forged promotion"
        assert any("illegal-promotion" in e for e in errors), errors


def test_deterministic_replay():
    hashes = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            led = _ledger(tmp)
            d = _append(led, state_from="UNKNOWN", state_to="PROPOSED")
            hashes.append(d["hash"])
    assert hashes[0] == hashes[1], "replay produced different hashes"


def test_evex_export_shape():
    with tempfile.TemporaryDirectory() as tmp:
        led = _ledger(tmp)
        d = _append(led, state_from="UNKNOWN", state_to="PROPOSED",
                    context={"domain_state": {"a": 1}, "sme_profile": {"b": 2},
                             "selection_receipt": {"c": 3},
                             "question_id": "Q7", "target_id": "TARGETER"})
        evex = cd.DeltaLedger.export_evex(d)
        # Base fields stand alone: a non-DESA-S consumer never reads adaptation.
        base = {k: v for k, v in evex.items() if k != "adaptation"}
        assert base["type"] == "state.transition" and base["version"] == "evex.v1"
        assert base["entity"] == "s" and base["state_from"] == "UNKNOWN"
        ad = evex["adaptation"]
        assert ad["profile"] == "desas-s.v1"
        assert ad["question_id"] == "Q7" and ad["target_id"] == "TARGETER"
        assert len(ad["domain_state_hash"]) == 64 and len(ad["sme_profile_hash"]) == 64


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"OK {len(tests)} tests")


if __name__ == "__main__":
    main()
