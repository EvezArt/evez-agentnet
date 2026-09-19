"""EVEZ causal-governance kernel.

Identity, intent, authorization, capability, action, execution, observation,
causal inference, independent verification, effect, and consequence remain
separate receipts. Later states never manufacture evidence for earlier states.

Steven/EVEZ and LORD are distinct objects. LORD is a governing system role.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid
from typing import Any, Iterable, Mapping

KERNEL_VERSION = "CGK/1"
ROLE_LORD = "LORD"
KINDS = (
    "IDENTITY", "INTENT", "AUTHORIZATION", "CAPABILITY", "ACTION", "EXECUTION",
    "OBSERVATION", "CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT",
    "CONSEQUENCE", "CAPABILITY_UPDATE", "REPUTATION_UPDATE", "NEGATIVE_SPACE",
    "ONTOLOGY_BREAK", "SUCCESSOR_CANDIDATE", "SUCCESSOR_TEST", "SUCCESSOR_DECISION",
)
UNCERTAINTY_AXES = (
    "identity", "intent", "authorization", "capability", "execution",
    "observation", "causal", "consequence", "ontology",
)

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"

@dataclass(frozen=True)
class Receipt:
    event_id: str
    kind: str
    observed_at: str
    parent_hash: str | None
    content_hash: str
    content: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "observed_at": self.observed_at,
            "parent_hash": self.parent_hash,
            "content_hash": self.content_hash,
            "content": self.content,
        }

class GovernanceError(ValueError):
    pass

class GovernanceChain:
    def __init__(self) -> None:
        self._events: list[Receipt] = []
        self._by_id: dict[str, Receipt] = {}

    @property
    def events(self) -> tuple[Receipt, ...]:
        return tuple(self._events)

    def _validate_timestamp(self, observed_at: str) -> None:
        try:
            datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GovernanceError("observed_at must be RFC 3339 date-time") from exc

    def append(
        self,
        kind: str,
        content: Mapping[str, Any],
        *,
        event_id: str | None = None,
        observed_at: str | None = None,
    ) -> Receipt:
        if kind not in KINDS:
            raise GovernanceError(f"unknown event kind: {kind}")
        observed_at = observed_at or now_rfc3339()
        self._validate_timestamp(observed_at)
        event_id = event_id or new_id(kind.lower())
        if event_id in self._by_id:
            raise GovernanceError(f"duplicate event_id: {event_id}")
        parent_hash = self._events[-1].content_hash if self._events else None
        body = {
            "event_id": event_id,
            "kind": kind,
            "observed_at": observed_at,
            "parent_hash": parent_hash,
            "content": dict(content),
        }
        content_hash = sha256(body)
        receipt = Receipt(
            event_id=event_id,
            kind=kind,
            observed_at=observed_at,
            parent_hash=parent_hash,
            content_hash=content_hash,
            content=dict(content),
        )
        self._events.append(receipt)
        self._by_id[event_id] = receipt
        return receipt

    def require(self, event_id: str) -> Receipt:
        try:
            return self._by_id[event_id]
        except KeyError as exc:
            raise GovernanceError(f"missing evidence/reference: {event_id}") from exc

    def verify(self) -> bool:
        parent: str | None = None
        seen: set[str] = set()
        for receipt in self._events:
            if receipt.event_id in seen:
                return False
            seen.add(receipt.event_id)
            body = {
                "event_id": receipt.event_id,
                "kind": receipt.kind,
                "observed_at": receipt.observed_at,
                "parent_hash": parent,
                "content": receipt.content,
            }
            if receipt.parent_hash != parent or receipt.content_hash != sha256(body):
                return False
            parent = receipt.content_hash
        return True

    def negative_space(
        self, subject: str, missing: Iterable[str], boundary: str, next_experiment: str
    ) -> Receipt:
        missing_list = sorted(set(missing))
        return self.append(
            "NEGATIVE_SPACE",
            {
                "subject": subject,
                "state": "NOT_YET_TESTED" if missing_list else "UNKNOWN",
                "missing_links": missing_list,
                "boundary": boundary,
                "resolution_condition": "Provide independently inspectable evidence for every missing link.",
                "next_experiment": next_experiment,
                "authority": "CLAIM_LOCAL_ONLY",
            },
        )

def situated_principal(
    chain: GovernanceChain,
    *,
    identity: str,
    system_role: str = ROLE_LORD,
    continuity_refs: Iterable[str] = (),
) -> Receipt:
    if identity == system_role:
        raise GovernanceError("identity must remain distinct from system role")
    return chain.append(
        "IDENTITY",
        {
            "identity": identity,
            "system_role": system_role,
            "relation": "SITUATED_IN",
            "identity_status": "HYPOTHESIS",
            "continuity_refs": sorted(set(continuity_refs)),
            "source_layer": "REAL",
            "authority": "CLAIM_LOCAL_ONLY",
        },
    )

def declare_intent(
    chain: GovernanceChain,
    *,
    principal_ref: str,
    objective: str,
    constraints: Mapping[str, Any] | None = None,
) -> Receipt:
    chain.require(principal_ref)
    return chain.append(
        "INTENT",
        {
            "principal_ref": principal_ref,
            "objective": objective,
            "constraints": dict(constraints or {}),
            "status": "PROPOSED",
        },
    )

def authorize(
    chain: GovernanceChain,
    *,
    principal_ref: str,
    intent_ref: str,
    authorization_ref: str,
    scope: Mapping[str, Any],
) -> Receipt:
    chain.require(principal_ref)
    chain.require(intent_ref)
    if not authorization_ref:
        raise GovernanceError("explicit authorization_ref is required")
    return chain.append(
        "AUTHORIZATION",
        {
            "principal_ref": principal_ref,
            "intent_ref": intent_ref,
            "authorization_ref": authorization_ref,
            "scope": dict(scope),
            "status": "AUTHORIZED_PENDING_EXECUTION",
        },
    )

def declare_capability(
    chain: GovernanceChain,
    *,
    capability: str,
    authority_ref: str,
    evidence_refs: Iterable[str] = (),
) -> Receipt:
    chain.require(authority_ref)
    return chain.append(
        "CAPABILITY",
        {
            "capability": capability,
            "authority_ref": authority_ref,
            "evidence_refs": sorted(set(evidence_refs)),
            "state": "DECLARED",
            "effective_claim_allowed": False,
        },
    )

def plan_action(
    chain: GovernanceChain,
    *,
    principal_ref: str,
    intent_ref: str,
    authorization_ref: str,
    capability_ref: str,
    action: Mapping[str, Any],
) -> Receipt:
    for ref in (principal_ref, intent_ref, authorization_ref, capability_ref):
        chain.require(ref)
    return chain.append(
        "ACTION",
        {
            "principal_ref": principal_ref,
            "governing_role": ROLE_LORD,
            "intent_ref": intent_ref,
            "authorization_ref": authorization_ref,
            "capability_ref": capability_ref,
            "action": dict(action),
            "status": "PLANNED",
        },
    )

def execution_receipt(
    chain: GovernanceChain,
    *,
    action_ref: str,
    executor: str,
    result_ref: str | None = None,
) -> Receipt:
    action = chain.require(action_ref)
    if action.kind != "ACTION":
        raise GovernanceError("execution requires ACTION receipt")
    return chain.append(
        "EXECUTION",
        {
            "action_ref": action.event_id,
            "executor": executor,
            "result_ref": result_ref,
            "status": "EXECUTED",
            "authority": action.content.get("authorization_ref"),
        },
    )

def observation_receipt(
    chain: GovernanceChain,
    *,
    execution_ref: str,
    observer: str,
    evidence_refs: Iterable[str],
    observed_effect: Mapping[str, Any],
) -> Receipt:
    execution = chain.require(execution_ref)
    if execution.kind != "EXECUTION":
        raise GovernanceError("observation requires EXECUTION receipt")
    evidence = sorted(set(evidence_refs))
    if not evidence:
        raise GovernanceError("observation requires evidence_refs")
    return chain.append(
        "OBSERVATION",
        {
            "execution_ref": execution_ref,
            "observer": observer,
            "evidence_refs": evidence,
            "observed_effect": dict(observed_effect),
            "observation_status": "OBSERVED",
        },
    )

def causal_hypothesis(
    chain: GovernanceChain,
    *,
    execution_ref: str,
    observation_ref: str,
    hypothesis: str,
) -> Receipt:
    execution = chain.require(execution_ref)
    observation = chain.require(observation_ref)
    if execution.kind != "EXECUTION" or observation.kind != "OBSERVATION":
        raise GovernanceError("causal hypothesis requires EXECUTION and OBSERVATION receipts")
    if observation.content.get("execution_ref") != execution_ref:
        raise GovernanceError("observation does not belong to execution")
    return chain.append(
        "CAUSAL_HYPOTHESIS",
        {
            "execution_ref": execution_ref,
            "observation_ref": observation_ref,
            "hypothesis": hypothesis,
            "status": "PROPOSED",
            "causal_claim": "HYPOTHESIS_ONLY",
        },
    )

def independent_verification(
    chain: GovernanceChain,
    *,
    hypothesis_ref: str,
    observation_ref: str,
    verifier: str,
    execution_actor: str,
    evidence_refs: Iterable[str],
) -> Receipt:
    hypothesis = chain.require(hypothesis_ref)
    observation = chain.require(observation_ref)
    if hypothesis.kind != "CAUSAL_HYPOTHESIS" or observation.kind != "OBSERVATION":
        raise GovernanceError("verification requires CAUSAL_HYPOTHESIS and OBSERVATION receipts")
    if hypothesis.content.get("observation_ref") != observation_ref:
        raise GovernanceError("hypothesis does not target observation")
    evidence = sorted(set(evidence_refs))
    if not evidence:
        raise GovernanceError("independent verification requires evidence_refs")
    if verifier == execution_actor:
        raise GovernanceError("independent verifier must differ from execution actor")
    return chain.append(
        "INDEPENDENT_VERIFICATION",
        {
            "hypothesis_ref": hypothesis_ref,
            "observation_ref": observation_ref,
            "verifier": verifier,
            "execution_actor": execution_actor,
            "evidence_refs": evidence,
            "status": "VERIFIED_WITHIN_EVIDENCE",
        },
    )

def effect_receipt(
    chain: GovernanceChain,
    *,
    hypothesis_ref: str,
    verification_ref: str,
    effect_ref: str,
) -> Receipt:
    hypothesis = chain.require(hypothesis_ref)
    verification = chain.require(verification_ref)
    effect_observation = chain.require(effect_ref)
    if hypothesis.kind != "CAUSAL_HYPOTHESIS":
        raise GovernanceError("effect requires CAUSAL_HYPOTHESIS receipt")
    if effect_observation.kind != "OBSERVATION":
        raise GovernanceError("effect_ref must identify an OBSERVATION receipt")
    if verification.kind != "INDEPENDENT_VERIFICATION":
        raise GovernanceError("effect requires independent verification")
    if verification.content.get("hypothesis_ref") != hypothesis_ref:
        raise GovernanceError("verification does not target hypothesis")
    if verification.content.get("observation_ref") != hypothesis.content.get("observation_ref"):
        raise GovernanceError("verification does not target hypothesis observation")
    if verification.kind != "INDEPENDENT_VERIFICATION":
        raise GovernanceError("effect requires independent verification")
    return chain.append(
        "EFFECT",
        {
            "hypothesis_ref": hypothesis_ref,
            "verification_ref": verification_ref,
            "effect_ref": effect_ref,
            "status": "CAUSALLY_VERIFIED_WITHIN_EVIDENCE",
            "truth_status": "NOT_ESTABLISHED",
        },
    )

def consequence_receipt(
    chain: GovernanceChain,
    *,
    effect_ref: str,
    consequence: Mapping[str, Any],
) -> Receipt:
    effect = chain.require(effect_ref)
    if effect.kind != "EFFECT":
        raise GovernanceError("consequence requires EFFECT receipt")
    return chain.append(
        "CONSEQUENCE",
        {
            "effect_ref": effect_ref,
            "consequence": dict(consequence),
            "status": "OBSERVED_OR_PROPOSED",
        },
    )

def causal_governance_gaps(chain: GovernanceChain, *, action_ref: str) -> list[str]:
    action = chain.require(action_ref)
    gaps: list[str] = []
    execution = next(
        (e for e in chain.events if e.kind == "EXECUTION" and e.content.get("action_ref") == action.event_id),
        None,
    )
    if execution is None:
        return ["EXECUTION"]
    observation = next(
        (e for e in chain.events if e.kind == "OBSERVATION" and e.content.get("execution_ref") == execution.event_id),
        None,
    )
    if observation is None:
        return ["OBSERVATION", "CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT"]
    hypothesis = next(
        (e for e in chain.events if e.kind == "CAUSAL_HYPOTHESIS" and e.content.get("observation_ref") == observation.event_id),
        None,
    )
    if hypothesis is None:
        return ["CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT"]
    verification = next(
        (e for e in chain.events if e.kind == "INDEPENDENT_VERIFICATION" and e.content.get("hypothesis_ref") == hypothesis.event_id),
        None,
    )
    if verification is None:
        return ["INDEPENDENT_VERIFICATION", "EFFECT"]
    if not any(e.kind == "EFFECT" and e.content.get("hypothesis_ref") == hypothesis.event_id for e in chain.events):
        gaps.append("EFFECT")
    return gaps

def uncertainty_vector(chain: GovernanceChain, *, action_ref: str) -> dict[str, str]:
    gaps = set(causal_governance_gaps(chain, action_ref=action_ref))
    state = {axis: "UNRESOLVED" for axis in UNCERTAINTY_AXES}
    state["identity"] = "DISTINGUISHED"
    state["intent"] = "RECORDED"
    state["authorization"] = "RECORDED"
    state["capability"] = "DECLARED_NOT_EFFECTIVE"
    state["execution"] = "OBSERVED" if "EXECUTION" not in gaps else "UNOBSERVED"
    state["observation"] = "OBSERVED" if "OBSERVATION" not in gaps else "UNOBSERVED"
    state["causal"] = (
        "VERIFIED_WITHIN_EVIDENCE"
        if "INDEPENDENT_VERIFICATION" not in gaps
        else "HYPOTHESIS_OR_UNKNOWN"
    )
    state["consequence"] = "OPEN"
    state["ontology"] = "NO_BREAK_OBSERVED"
    return state

def propose_successor(
    chain: GovernanceChain,
    *,
    break_ref: str,
    prior_model: str,
    candidate_model: str,
    discriminator: str,
    falsifier: str,
) -> Receipt:
    chain.require(break_ref)
    return chain.append(
        "SUCCESSOR_CANDIDATE",
        {
            "break_ref": break_ref,
            "prior_model": prior_model,
            "candidate_model": candidate_model,
            "discriminator": discriminator,
            "falsifier": falsifier,
            "status": "PROPOSED",
            "authority": "CLAIM_LOCAL_ONLY",
        },
    )

def succession_decision(
    chain: GovernanceChain,
    *,
    candidate_ref: str,
    test_ref: str,
    evidence_refs: Iterable[str],
    decision: str,
    authorization_ref: str | None = None,
) -> Receipt:
    chain.require(candidate_ref)
    chain.require(test_ref)
    refs = sorted(set(evidence_refs))
    if decision == "ADOPTED" and (not refs or not authorization_ref):
        raise GovernanceError("adoption requires evidence_refs and authorization_ref")
    return chain.append(
        "SUCCESSOR_DECISION",
        {
            "candidate_ref": candidate_ref,
            "test_ref": test_ref,
            "evidence_refs": refs,
            "decision": decision,
            "authorization_ref": authorization_ref,
            "status": "DECIDED",
        },
    )
