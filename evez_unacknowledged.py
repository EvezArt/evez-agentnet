#!/usr/bin/env python3
"""EVEZ unacknowledged semantic layer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

STATES = (
    "OBSERVED", "SUPPORTED", "INFERRED", "PROPOSED", "UNKNOWN",
    "INACCESSIBLE", "CONTRADICTED", "STALE", "RETRACTED",
)
NEGATIVE_SPACE_STATES = (
    "NOT_FOUND", "NOT_OBSERVED", "NOT_AUTHORIZED", "NOT_REACHABLE",
    "NOT_SUPPORTED", "NOT_YET_TESTED", "CONTRADICTED", "STALE", "UNKNOWN",
)
PROTOCOL_STEPS = (
    "DISCOVER", "IDENTIFY", "DECLARE", "CHALLENGE", "NEGOTIATE",
    "AUTHORIZE", "EXECUTE", "OBSERVE", "VERIFY", "COMMIT", "REMEMBER",
)
CAPABILITY_STATES = (
    "DISCOVERED", "DECLARED", "PERMITTED", "TESTED", "EFFECTIVE",
    "COMPOSED", "VERIFIED", "PUBLISHED", "DEPRECATED", "REVOKED",
)
SOURCE_LAYERS = ("REAL", "SIMULATED", "DERIVED", "HYPOTHETICAL", "CROSS_DOMAIN")

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def _require(value: Any, name: str) -> Any:
    if value is None or value == "":
        raise ValueError(f"{name} is required")
    return value

def _enum(value: str, allowed: Sequence[str], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}")
    return value

def make_event(event_type: str, payload: Mapping[str, Any], *, observed_at: str,
               parent_hash: str | None = None, source_layer: str = "DERIVED") -> dict[str, Any]:
    _require(event_type, "event_type")
    _require(observed_at, "observed_at")
    _enum(source_layer, SOURCE_LAYERS, "source_layer")
    body = {
        "event_type": event_type,
        "observed_at": observed_at,
        "source_layer": source_layer,
        "payload": dict(payload),
    }
    body["content_hash"] = sha256(body)
    body["parent_hash"] = parent_hash
    body["event_hash"] = sha256(body)
    return body

def append_event(path: str | Path, event_type: str, payload: Mapping[str, Any], *,
                 observed_at: str, source_layer: str = "DERIVED") -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    parent_hash = None
    if target.exists():
        lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            parent_hash = json.loads(lines[-1])["event_hash"]
    event = make_event(event_type, payload, observed_at=observed_at,
                       parent_hash=parent_hash, source_layer=source_layer)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    return event

def verify_chain(path: str | Path) -> tuple[bool, list[str]]:
    target = Path(path)
    if not target.exists():
        return True, []
    errors: list[str] = []
    parent = None
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            expected_content = dict(event)
            expected_content.pop("content_hash", None)
            expected_content.pop("event_hash", None)
            if sha256(expected_content) != event.get("content_hash"):
                errors.append(f"line {number}: content_hash mismatch")
            expected_event = dict(event)
            expected_event.pop("event_hash", None)
            if sha256(expected_event) != event.get("event_hash"):
                errors.append(f"line {number}: event_hash mismatch")
            if event.get("parent_hash") != parent:
                errors.append(f"line {number}: parent_hash mismatch")
            parent = event.get("event_hash")
        except (json.JSONDecodeError, KeyError, TypeError):
            errors.append(f"line {number}: invalid event")
    return not errors, errors

def situated_capability(capability_id: str, *, declared: bool, context: Mapping[str, Any],
                        authority: Mapping[str, Any], observation: Mapping[str, Any],
                        effect: Mapping[str, Any], capability_state: str = "DECLARED") -> dict[str, Any]:
    _require(capability_id, "capability_id")
    _enum(capability_state, CAPABILITY_STATES, "capability_state")
    return {
        "capability_id": capability_id,
        "declared": bool(declared),
        "context": dict(context),
        "authority": dict(authority),
        "observation": dict(observation),
        "effect": dict(effect),
        "capability_state": capability_state,
        "effective_claim_allowed": capability_state in {"EFFECTIVE", "COMPOSED", "VERIFIED", "PUBLISHED"},
    }

def negative_space(subject: str, state: str, *, boundary: Mapping[str, Any],
                   resolution_condition: str, next_experiment: str,
                   evidence_refs: Iterable[str] = ()) -> dict[str, Any]:
    _require(subject, "subject")
    _enum(state, NEGATIVE_SPACE_STATES, "state")
    _require(resolution_condition, "resolution_condition")
    _require(next_experiment, "next_experiment")
    return {
        "subject": subject,
        "state": state,
        "boundary": dict(boundary),
        "resolution_condition": resolution_condition,
        "next_experiment": next_experiment,
        "evidence_refs": list(evidence_refs),
    }

def latent_requirements(intent: str, *, declared_capabilities: Iterable[str] = (),
                        known_boundaries: Iterable[str] = ()) -> dict[str, Any]:
    text = intent.lower()
    rules = {
        "browser": ["page_state", "identity", "navigation_history", "side_effect_capture"],
        "web": ["reality_surface", "protocol_discovery", "provenance"],
        "sync": ["identity_resolution", "versioning", "deduplication", "change_detection"],
        "world": ["institutions", "economics", "social_knowledge", "historical_scars"],
        "agent": ["capability_context", "authority_boundary", "prediction_error", "handoff"],
        "build": ["test_condition", "reproducibility", "artifact_ancestry", "failure_record"],
        "run": ["observation", "effect", "provenance", "recovery"],
    }
    proposed: list[dict[str, Any]] = []
    for trigger, requirements in rules.items():
        if trigger in text:
            for requirement in requirements:
                proposed.append({"state": "PROPOSED", "trigger": trigger, "requirement": requirement})
    return {
        "intent": intent,
        "state": "PROPOSED",
        "requirements": proposed,
        "declared_capabilities": list(declared_capabilities),
        "known_boundaries": list(known_boundaries),
    }

def prediction(prediction_id: str, *, model_ref: str, expected: Any, action_ref: str,
               observed: Any | None = None, observed_at: str | None = None) -> dict[str, Any]:
    _require(prediction_id, "prediction_id")
    _require(model_ref, "model_ref")
    record: dict[str, Any] = {
        "prediction_id": prediction_id,
        "model_ref": model_ref,
        "expected": expected,
        "action_ref": action_ref,
        "status": "PENDING",
    }
    if observed_at is not None:
        record["observed_at"] = observed_at
    if observed is not None:
        record["observed"] = observed
        record["status"] = "OBSERVED"
        record["surprise"] = observed != expected
        record["error"] = {"expected": expected, "observed": observed} if observed != expected else None
    return record

def witness(witness_id: str, *, origin: str, transformations: Iterable[str] = (),
            observations: Iterable[str] = (), contradictions: Iterable[str] = (),
            continuity_basis: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "witness_id": _require(witness_id, "witness_id"),
        "origin": _require(origin, "origin"),
        "transformations": list(transformations),
        "observations": list(observations),
        "contradictions": list(contradictions),
        "continuity_basis": list(continuity_basis),
        "identity_status": "HYPOTHESIS",
    }

def ontology_break(break_id: str, *, prior_model: str, observation: Any,
                   failed_representation: str, contradiction: Iterable[str] = (),
                   proposed_distinctions: Iterable[str] = (),
                   affected_capabilities: Iterable[str] = (),
                   affected_protocols: Iterable[str] = (),
                   witnesses: Iterable[str] = (), tests: Iterable[str] = ()) -> dict[str, Any]:
    _require(break_id, "break_id")
    _require(prior_model, "prior_model")
    _require(failed_representation, "failed_representation")
    return {
        "break_id": break_id,
        "event": "ONTOLOGICAL_BREAK",
        "prior_model": prior_model,
        "observation": observation,
        "failed_representation": failed_representation,
        "contradiction": list(contradiction),
        "proposed_distinctions": list(proposed_distinctions),
        "affected_capabilities": list(affected_capabilities),
        "affected_protocols": list(affected_protocols),
        "witnesses": list(witnesses),
        "tests": list(tests),
        "successor_model": None,
        "status": "OPEN",
    }

def capability_mutation(capability_id: str, *, parents: Iterable[str], mutation: str,
                        test_refs: Iterable[str] = (), environment: str,
                        evidence_refs: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "capability_id": _require(capability_id, "capability_id"),
        "parents": list(parents),
        "mutation": _require(mutation, "mutation"),
        "test_refs": list(test_refs),
        "environment": _require(environment, "environment"),
        "evidence_refs": list(evidence_refs),
        "state": "PROPOSED",
    }

def protocol_discovery(protocol_id: str, *, surface_ref: str,
                       observed_steps: Iterable[str], identities: Iterable[str] = (),
                       public_operations: Iterable[str] = (),
                       authorization_boundaries: Iterable[str] = ()) -> dict[str, Any]:
    steps = list(observed_steps)
    invalid = [step for step in steps if step not in PROTOCOL_STEPS]
    if invalid:
        raise ValueError(f"unknown protocol steps: {', '.join(invalid)}")
    return {
        "protocol_id": _require(protocol_id, "protocol_id"),
        "surface_ref": _require(surface_ref, "surface_ref"),
        "observed_steps": steps,
        "identities": list(identities),
        "public_operations": list(public_operations),
        "authorization_boundaries": list(authorization_boundaries),
        "status": "PROVISIONAL",
    }

def question(question_id: str, *, statement: str, origin_event: str,
             resolution_condition: str, required_instruments: Iterable[str] = (),
             status: str = "UNRESOLVED") -> dict[str, Any]:
    return {
        "question_id": _require(question_id, "question_id"),
        "statement": _require(statement, "statement"),
        "origin_event": _require(origin_event, "origin_event"),
        "resolution_condition": _require(resolution_condition, "resolution_condition"),
        "required_instruments": list(required_instruments),
        "status": status,
    }

def scar(scar_id: str, *, origin_event: str, state_change: Mapping[str, Any],
         future_constraints: Mapping[str, Any], affected_surfaces: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "scar_id": _require(scar_id, "scar_id"),
        "origin_event": _require(origin_event, "origin_event"),
        "state_change": dict(state_change),
        "future_constraints": dict(future_constraints),
        "affected_surfaces": list(affected_surfaces),
    }

def handshake(*, participant: str, steps: Iterable[str],
              authorization_evidence: Iterable[str] = ()) -> dict[str, Any]:
    actual = list(steps)
    invalid = [step for step in actual if step not in PROTOCOL_STEPS]
    if invalid:
        raise ValueError(f"unknown protocol steps: {', '.join(invalid)}")
    auth = list(authorization_evidence)
    if "AUTHORIZE" in actual and not auth:
        raise ValueError("AUTHORIZE requires authorization_evidence")
    return {
        "participant": _require(participant, "participant"),
        "steps": actual,
        "authorization_evidence": auth,
        "state": "PROVISIONAL" if "VERIFY" not in actual else "VERIFIED",
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Append an EVEZ unacknowledged-layer event.")
    parser.add_argument("ledger")
    parser.add_argument("event_type")
    parser.add_argument("observed_at")
    parser.add_argument("payload_json")
    parser.add_argument("--source-layer", default="DERIVED")
    args = parser.parse_args()
    event = append_event(
        args.ledger, args.event_type, json.loads(args.payload_json),
        observed_at=args.observed_at, source_layer=args.source_layer,
    )
    print(json.dumps(event, sort_keys=True, ensure_ascii=False))

if __name__ == "__main__":
    main()
