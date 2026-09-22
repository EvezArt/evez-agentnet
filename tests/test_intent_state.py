from daemon.intent_state import (
    IntentSignal,
    IntentStatus,
    UserIntentState,
    infer_intent,
)


def test_correction_overrides_inferred_objective():
    state = UserIntentState()
    state.observe("execute", [IntentSignal("trajectory", "execute now", 1.0)])
    assert state.active_objective == "execute"

    state.apply_correction("compute", "do the computation, not the explanation")
    assert state.active_objective == "compute"
    assert state.correction_count == 1


def test_explicit_objective_has_authority():
    state = UserIntentState()
    state.observe("explain", [IntentSignal("trajectory", "explain architecture", 1.0)])
    state.set_explicit_objective("execute")
    assert state.active_objective == "execute"


def test_intent_is_not_certainty():
    state = UserIntentState()
    hypothesis = state.observe(
        "execute",
        [IntentSignal("trajectory", "execute", 1.0)],
    )
    assert hypothesis.status == IntentStatus.SUPPORTED
    assert hypothesis.confidence <= 1.0


def test_state_hash_is_deterministic():
    state = UserIntentState()
    state.observe(
        "compute",
        [IntentSignal("correction", "compute rather than explain", 1.0)],
    )
    assert state.state_hash() == state.state_hash()


def test_infer_intent_uses_observable_signals_only():
    signals = [
        IntentSignal("explicit", "compute the next state", 1.0),
        IntentSignal("correction", "not explanation", 1.0),
    ]
    result = infer_intent(signals, ["compute", "explain"])
    assert result is not None
    assert result.objective == "compute"


def test_explicit_objective_contradicts_prior_hypothesis_and_supports_target():
    state = UserIntentState()
    state.observe("explain", [IntentSignal("trajectory", "explain architecture", 1.0)])
    state.set_explicit_objective("execute")

    assert state.active_objective == "execute"
    assert state.hypotheses["explain"].status == IntentStatus.CONTRADICTED
    assert state.hypotheses["execute"].status == IntentStatus.SUPPORTED


def test_negated_candidate_is_not_positive_evidence():
    signals = [IntentSignal("correction", "not compute, explain instead", 1.0)]
    result = infer_intent(signals, ["compute", "explain"])

    assert result is not None
    assert result.objective == "explain"
    assert result.score > 0
