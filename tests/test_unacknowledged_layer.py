#!/usr/bin/env python3
from __future__ import annotations
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evez_unacknowledged import (
    append_event, capability_mutation, handshake, latent_requirements,
    negative_space, ontology_break, prediction, situated_capability,
    verify_chain, witness,
)

def test_chain():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "events.jsonl"
        first = append_event(ledger, "OBSERVATION", {"value": 1}, observed_at="2026-09-19T00:00:00Z")
        second = append_event(ledger, "REVISION", {"value": 2}, observed_at="2026-09-19T00:01:00Z")
        assert second["parent_hash"] == first["event_hash"]
        assert verify_chain(ledger) == (True, [])
    ledger.write_text(ledger.read_text() + "[1,2]\n", encoding="utf-8")
    ok, errors = verify_chain(ledger)
    assert ok is False and any("invalid event" in e for e in errors)

def test_situated_capability():
    record = situated_capability(
        "browser.navigate", declared=True,
        context={"surface": "example", "session": "s1"},
        authority={"principal": "p1", "scope": ["public"]},
        observation={"tested": False}, effect={"observed": False},
    )
    assert record["capability_state"] == "DECLARED"
    assert record["effective_claim_allowed"] is False

def test_negative_space():
    record = negative_space(
        "missing plugin entrypoint", "NOT_FOUND",
        boundary={"repository": "inspected", "ref": "main"},
        resolution_condition="file appears at the declared path",
        next_experiment="inspect the exact commit tree",
    )
    assert record["state"] == "NOT_FOUND"

def test_latent_requirements():
    result = latent_requirements("Build a browser agent")
    assert result["state"] == "PROPOSED"
    assert all(item["state"] == "PROPOSED" for item in result["requirements"])

def test_invalid_timestamp():
    try:
        append_event(Path(tempfile.mkdtemp()) / "events.jsonl", "OBSERVATION", {}, observed_at="not-a-date")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid timestamp must fail")

def test_prediction():
    result = prediction(
        "p1", model_ref="model:1", expected={"status": "ok"}, action_ref="run:1",
        observed={"status": "error"}, observed_at="2026-09-19T00:00:00Z",
    )
    assert result["surprise"] is True
    assert result["error"]["expected"]["status"] == "ok"
    null_result = prediction("p2", model_ref="model:1", expected=1, action_ref="run:2", observed=None)
    assert null_result["status"] == "OBSERVED"

def test_ontology_break():
    result = ontology_break(
        "break-1", prior_model="AGENT",
        observation={"behavior": "distributed"},
        failed_representation="single principal cannot represent the observation",
        proposed_distinctions=["COLLECTIVE_AGENT", "INSTRUMENTATION_ARTIFACT"],
    )
    assert result["prior_model"] == "AGENT"
    assert result["successor_model"] is None
    assert result["status"] == "OPEN"

def test_genealogy_and_protocol():
    mutation = capability_mutation(
        "TRACE", parents=["SEARCH", "BROWSE", "EXTRACT", "VERIFY"],
        mutation="causal surface trace", environment="public-research",
    )
    assert mutation["state"] == "PROPOSED"
    try:
        handshake(participant="surface:1", steps=["DISCOVER", "AUTHORIZE"])
    except ValueError:
        pass
    else:
        raise AssertionError("authorization without evidence must fail")
    try:
        handshake(participant="surface:1", steps=["VERIFY"])
    except ValueError:
        pass
    else:
        raise AssertionError("VERIFY without OBSERVE must fail")
    verified = handshake(participant="surface:1", steps=["OBSERVE", "VERIFY"], authorization_evidence=["obs:1"])
    assert verified["state"] == "VERIFIED"

def test_witness():
    result = witness("w1", origin="artifact:0", continuity_basis=["shared hash ancestry"])
    assert result["identity_status"] == "HYPOTHESIS"

if __name__ == "__main__":
    tests = [test_chain, test_situated_capability, test_negative_space,
             test_latent_requirements, test_invalid_timestamp, test_prediction, test_ontology_break,
             test_genealogy_and_protocol, test_witness]
    for test in tests:
        test()
    print(f"ok: {len(tests)} tests")
