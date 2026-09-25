import pytest

from tools.causal_governance import (
    GovernanceChain,
    GovernanceError,
    causal_governance_gaps,
    causal_hypothesis,
    declare_capability,
    declare_intent,
    effect_receipt,
    execution_receipt,
    independent_verification,
    observation_receipt,
    plan_action,
    situated_principal,
    uncertainty_vector,
)


def build_action_chain():
    chain = GovernanceChain()
    identity = situated_principal(chain, identity="Steven/EVEZ")
    intent = declare_intent(chain, principal_ref=identity.event_id, objective="test")
    auth = chain.append(
        "AUTHORIZATION",
        {
            "principal_ref": identity.event_id,
            "intent_ref": intent.event_id,
            "authorization_ref": "human-approval-1",
            "scope": {"mode": "test"},
            "status": "AUTHORIZED_PENDING_EXECUTION",
        },
    )
    cap = declare_capability(chain, capability="test.execute", authority_ref=auth.event_id)
    action = plan_action(
        chain,
        principal_ref=identity.event_id,
        intent_ref=intent.event_id,
        authorization_ref=auth.event_id,
        capability_ref=cap.event_id,
        action={"operation": "noop"},
    )
    execution = execution_receipt(chain, action_ref=action.event_id, executor="worker-A")
    return chain, action, execution


def test_identity_is_not_lord_role():
    chain = GovernanceChain()
    rec = situated_principal(chain, identity="Steven/EVEZ")
    assert rec.content["identity"] != rec.content["system_role"]
    assert rec.content["relation"] == "SITUATED_IN"


def test_missing_observation_stays_open():
    chain, action, _ = build_action_chain()
    gaps = causal_governance_gaps(chain, action_ref=action.event_id)
    assert gaps == ["OBSERVATION", "CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT"]


def test_observation_requires_evidence():
    chain, _, execution = build_action_chain()
    with pytest.raises(GovernanceError):
        observation_receipt(
            chain,
            execution_ref=execution.event_id,
            observer="observer-A",
            evidence_refs=[],
            observed_effect={"changed": True},
        )


def test_verifier_must_be_independent():
    chain, _, execution = build_action_chain()
    obs = observation_receipt(
        chain,
        execution_ref=execution.event_id,
        observer="worker-A",
        evidence_refs=["sensor-receipt-1"],
        observed_effect={"changed": True},
    )
    hyp = causal_hypothesis(
        chain,
        execution_ref=execution.event_id,
        observation_ref=obs.event_id,
        hypothesis="execution contributed to change",
    )
    with pytest.raises(GovernanceError):
        independent_verification(
            chain,
            hypothesis_ref=hyp.event_id,
            observation_ref=obs.event_id,
            verifier="worker-A",
            execution_actor="worker-A",
            evidence_refs=["independent-check-1"],
        )


def test_independent_verification_unlocks_effect_but_not_truth():
    chain, _, execution = build_action_chain()
    obs = observation_receipt(
        chain,
        execution_ref=execution.event_id,
        observer="observer-A",
        evidence_refs=["sensor-receipt-1"],
        observed_effect={"changed": True},
    )
    hyp = causal_hypothesis(
        chain,
        execution_ref=execution.event_id,
        observation_ref=obs.event_id,
        hypothesis="execution contributed to change",
    )
    ver = independent_verification(
        chain,
        hypothesis_ref=hyp.event_id,
        observation_ref=obs.event_id,
        verifier="verifier-B",
        execution_actor="worker-A",
        evidence_refs=["independent-check-1"],
    )
    eff = effect_receipt(
        chain,
        hypothesis_ref=hyp.event_id,
        verification_ref=ver.event_id,
        effect_ref=obs.event_id,
    )
    assert eff.content["status"] == "CAUSALLY_VERIFIED_WITHIN_EVIDENCE"
    assert eff.content["truth_status"] == "NOT_ESTABLISHED"
    assert chain.verify()


def test_chain_tamper_is_detected():
    chain, _, _ = build_action_chain()
    raw = chain._events[-1]
    raw.content["status"] = "tampered"
    assert not chain.verify()


def test_uncertainty_vector_preserves_open_causal_state():
    chain, action, _ = build_action_chain()
    vector = uncertainty_vector(chain, action_ref=action.event_id)
    assert vector["execution"] == "OBSERVED"
    assert vector["observation"] == "UNOBSERVED"
    assert vector["causal"] == "HYPOTHESIS_OR_UNKNOWN"


def test_receipt_reference_types_are_enforced():
    chain, action, execution = build_action_chain()
    with pytest.raises(GovernanceError):
        observation_receipt(
            chain,
            execution_ref=action.event_id,
            observer="observer-A",
            evidence_refs=["evidence"],
            observed_effect={"changed": True},
        )
    obs = observation_receipt(
        chain,
        execution_ref=execution.event_id,
        observer="observer-A",
        evidence_refs=["sensor"],
        observed_effect={"changed": True},
    )
    with pytest.raises(GovernanceError):
        causal_hypothesis(
            chain,
            execution_ref=action.event_id,
            observation_ref=obs.event_id,
            hypothesis="bad reference",
        )


def test_effect_requires_matching_verification_targets():
    chain, _, execution = build_action_chain()
    obs = observation_receipt(
        chain,
        execution_ref=execution.event_id,
        observer="observer-A",
        evidence_refs=["sensor"],
        observed_effect={"changed": True},
    )
    hyp = causal_hypothesis(
        chain,
        execution_ref=execution.event_id,
        observation_ref=obs.event_id,
        hypothesis="execution contributed to change",
    )
    wrong = chain.append(
        "INDEPENDENT_VERIFICATION",
        {
            "hypothesis_ref": "different-hypothesis",
            "observation_ref": obs.event_id,
            "verifier": "verifier-B",
            "execution_actor": "worker-A",
            "evidence_refs": ["independent"],
        },
    )
    with pytest.raises(GovernanceError):
        effect_receipt(
            chain,
            hypothesis_ref=hyp.event_id,
            verification_ref=wrong.event_id,
            effect_ref=obs.event_id,
        )
