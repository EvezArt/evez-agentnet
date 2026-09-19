#!/usr/bin/env python3
"""Causal economic witness: provenance-safe coupling between reality, delivery, and money."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Mapping, Sequence

MONEY_STATES = ("PROPOSED", "CONTRACTED", "INVOICED", "RECEIVED")
REALITY_LAYERS = ("REAL", "SIMULATED", "DERIVED", "HYPOTHETICAL", "CROSS_DOMAIN")
CAPABILITY_STATES = ("DISCOVERED","DECLARED","PERMITTED","TESTED","EFFECTIVE","COMPOSED","VERIFIED","PUBLISHED","DEPRECATED","REVOKED")

class CausalError(ValueError):
    pass

def _req(value: Any, name: str) -> Any:
    if value is None or value == "" or value == []:
        raise CausalError(f"{name} is required")
    return value

def _one_of(value: str, allowed: Sequence[str], name: str) -> str:
    if value not in allowed:
        raise CausalError(f"{name} must be one of {', '.join(allowed)}")
    return value

def _refs(values: Iterable[str]) -> list[str]:
    return [_req(v, "evidence_ref") for v in values]

@dataclass(frozen=True)
class EconomicState:
    opportunity_id: str
    state: str
    amount: float | int | None
    currency: str | None
    evidence_refs: tuple[str, ...]
    source_layer: str = "DERIVED"
    def __post_init__(self) -> None:
        _req(self.opportunity_id, "opportunity_id")
        _one_of(self.state, MONEY_STATES, "state")
        _one_of(self.source_layer, REALITY_LAYERS, "source_layer")
        if self.amount is not None and self.amount < 0:
            raise CausalError("amount cannot be negative")
        if self.state == "RECEIVED" and not self.evidence_refs:
            raise CausalError("RECEIVED requires observed payment evidence")
        if self.state in {"CONTRACTED","INVOICED"} and self.source_layer == "REAL" and not self.evidence_refs:
            raise CausalError("REAL economic states require evidence_refs")
    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["evidence_refs"] = list(self.evidence_refs)
        return out

def economic_state(opportunity_id: str, state: str, *, amount: float | int | None = None,
                   currency: str | None = None, evidence_refs: Iterable[str] = (),
                   source_layer: str = "DERIVED") -> dict[str, Any]:
    return EconomicState(opportunity_id, state, amount, currency, tuple(evidence_refs), source_layer).as_dict()

def validate_transition(previous: str | None, next_state: str) -> bool:
    _one_of(next_state, MONEY_STATES, "next_state")
    if previous is None:
        return True
    _one_of(previous, MONEY_STATES, "previous")
    order = {name: i for i, name in enumerate(MONEY_STATES)}
    if order[next_state] < order[previous]:
        raise CausalError(f"illegal regression: {previous} -> {next_state}")
    return True

def transition(opportunity_id: str, *, previous_state: str | None, next_state: str,
               evidence_refs: Iterable[str] = (), reason: str, observed_at: str) -> dict[str, Any]:
    _req(observed_at, "observed_at")
    _req(reason, "reason")
    validate_transition(previous_state, next_state)
    refs = _refs(evidence_refs)
    if next_state == "RECEIVED" and not refs:
        raise CausalError("OBSERVED_PAYMENT requires evidence_refs")
    return {"event_type":"ECONOMIC_STATE_TRANSITION","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "previous_state":previous_state,"next_state":next_state,"reason":reason,
            "observed_at":observed_at,"evidence_refs":refs}

def capability_match(opportunity_id: str, capability_id: str, *, match_basis: Iterable[str],
                     capability_state: str) -> dict[str, Any]:
    _one_of(capability_state, CAPABILITY_STATES, "capability_state")
    return {"event_type":"CAPABILITY_MATCH","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "capability_id":_req(capability_id,"capability_id"),"match_basis":_refs(match_basis),
            "capability_state":capability_state,"claim_level":"MATCH_PROPOSED"}

def approval_gate(opportunity_id: str, *, approver_ref: str, decision: str,
                  approved_scope: Mapping[str, Any], evidence_refs: Iterable[str] = ()) -> dict[str, Any]:
    return {"event_type":"HUMAN_APPROVAL","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "approver_ref":_req(approver_ref,"approver_ref"),
            "decision":_one_of(decision,("APPROVED","REJECTED","EXPIRED"),"decision"),
            "approved_scope":dict(approved_scope),"evidence_refs":_refs(evidence_refs)}

def contract_gate(opportunity_id: str, *, approval_ref: str, contract_ref: str,
                  contract_terms: Mapping[str, Any]) -> dict[str, Any]:
    return {"event_type":"CONTRACT","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "approval_ref":_req(approval_ref,"approval_ref"),"contract_ref":_req(contract_ref,"contract_ref"),
            "contract_terms":dict(contract_terms)}

def delivery_receipt(opportunity_id: str, *, contract_ref: str, artifact_refs: Iterable[str],
                     delivery_evidence_refs: Iterable[str], observed_at: str) -> dict[str, Any]:
    return {"event_type":"DELIVERY","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "contract_ref":_req(contract_ref,"contract_ref"),"artifact_refs":_refs(artifact_refs),
            "delivery_evidence_refs":_refs(delivery_evidence_refs),"observed_at":_req(observed_at,"observed_at")}

def payment_observation(opportunity_id: str, *, amount: float | int, currency: str,
                        payment_evidence_refs: Iterable[str], observed_at: str) -> dict[str, Any]:
    refs = _refs(payment_evidence_refs)
    if amount < 0:
        raise CausalError("amount cannot be negative")
    return {"event_type":"OBSERVED_PAYMENT","opportunity_id":_req(opportunity_id,"opportunity_id"),
            "amount":amount,"currency":_req(currency,"currency"),"payment_evidence_refs":refs,
            "observed_at":_req(observed_at,"observed_at"),"claim":"RECEIVED"}

def causal_receipt(*, receipt_id: str, opportunity_id: str, upstream_refs: Iterable[str],
                   downstream_refs: Iterable[str], verified_delivery: bool,
                   observed_payment: bool) -> dict[str, Any]:
    if observed_payment and not verified_delivery:
        raise CausalError("payment cannot certify delivery unless delivery is independently verified")
    return {"event_type":"CAUSAL_RECEIPT","receipt_id":_req(receipt_id,"receipt_id"),
            "opportunity_id":_req(opportunity_id,"opportunity_id"),"upstream_refs":_refs(upstream_refs),
            "downstream_refs":_refs(downstream_refs),"verified_delivery":bool(verified_delivery),
            "observed_payment":bool(observed_payment),
            "causal_claim":"DELIVERY_TO_PAYMENT_PATH_OBSERVED" if verified_delivery and observed_payment else "LINEAGE_ONLY"}

def capability_update(capability_id: str, *, mutation: str, delivery_refs: Iterable[str],
                      verification_refs: Iterable[str], environment: str) -> dict[str, Any]:
    verification = _refs(verification_refs)
    return {"event_type":"CAPABILITY_MUTATION","capability_id":_req(capability_id,"capability_id"),
            "mutation":_req(mutation,"mutation"),"delivery_refs":_refs(delivery_refs),
            "verification_refs":verification,"environment":_req(environment,"environment"),
            "state":"VERIFIED" if verification else "PROPOSED"}
