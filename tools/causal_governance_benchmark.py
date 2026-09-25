"""Deterministic benchmark for EVEZ causal-governance behavior."""
from __future__ import annotations

import json

from tools.causal_governance import (
    GovernanceChain,
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
)


def fixture() -> tuple[GovernanceChain, object, object]:
    chain = GovernanceChain()
    identity = situated_principal(chain, identity="Steven/EVEZ")
    intent = declare_intent(chain, principal_ref=identity.event_id, objective="benchmark")
    auth = chain.append(
        "AUTHORIZATION",
        {
            "principal_ref": identity.event_id,
            "intent_ref": intent.event_id,
            "authorization_ref": "fixture-approval",
            "scope": {"benchmark": True},
        },
    )
    cap = declare_capability(chain, capability="fixture.execute", authority_ref=auth.event_id)
    action = plan_action(
        chain,
        principal_ref=identity.event_id,
        intent_ref=intent.event_id,
        authorization_ref=auth.event_id,
        capability_ref=cap.event_id,
        action={"operation": "deterministic-fixture"},
    )
    execution = execution_receipt(chain, action_ref=action.event_id, executor="fixture-runner")
    return chain, action, execution


def run_benchmark() -> dict:
    results = []

    chain, action, execution = fixture()
    results.append({
        "case": "execution_without_observation",
        "pass": causal_governance_gaps(chain, action_ref=action.event_id)
        == ["OBSERVATION", "CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT"],
    })

    obs = observation_receipt(
        chain,
        execution_ref=execution.event_id,
        observer="fixture-observer",
        evidence_refs=["observation-fixture"],
        observed_effect={"changed": True},
    )
    results.append({
        "case": "observation_without_causality",
        "pass": causal_governance_gaps(chain, action_ref=action.event_id)
        == ["CAUSAL_HYPOTHESIS", "INDEPENDENT_VERIFICATION", "EFFECT"],
    })

    hyp = causal_hypothesis(
        chain,
        execution_ref=execution.event_id,
        observation_ref=obs.event_id,
        hypothesis="fixture execution contributed to fixture change",
    )
    results.append({
        "case": "hypothesis_without_independent_verification",
        "pass": causal_governance_gaps(chain, action_ref=action.event_id)
        == ["INDEPENDENT_VERIFICATION", "EFFECT"],
    })

    ver = independent_verification(
        chain,
        hypothesis_ref=hyp.event_id,
        observation_ref=obs.event_id,
        verifier="independent-fixture-verifier",
        execution_actor="fixture-runner",
        evidence_refs=["verification-fixture"],
    )
    results.append({
        "case": "independent_verification_without_effect",
        "pass": causal_governance_gaps(chain, action_ref=action.event_id) == ["EFFECT"],
    })

    eff = effect_receipt(
        chain,
        hypothesis_ref=hyp.event_id,
        verification_ref=ver.event_id,
        effect_ref=obs.event_id,
    )
    results.append({
        "case": "causal_effect_after_independent_verification",
        "pass": causal_governance_gaps(chain, action_ref=action.event_id) == []
        and eff.content["truth_status"] == "NOT_ESTABLISHED",
    })

    results.append({
        "case": "append_only_chain_verifies",
        "pass": chain.verify(),
    })

    return {
        "benchmark": "EVEZ-CGK/1",
        "cases": results,
        "passed": sum(1 for r in results if r["pass"]),
        "total": len(results),
    }


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), sort_keys=True, indent=2))
