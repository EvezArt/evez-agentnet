from daemon.intent_trajectory import summarize


def test_trajectory_requires_minimum_evidence():
    events = [
        {
            "event": "intent_state",
            "active_objective": "compute",
            "result": {"status": "completed", "aligned": True},
        }
    ]
    t = summarize(events, "compute", minimum_samples=3)
    assert t.evidence_status == "UNKNOWN"
    assert t.alignment_rate is None


def test_trajectory_summarizes_committed_outcomes():
    events = [
        {
            "event": "intent_state",
            "active_objective": "compute",
            "result": {"status": "completed", "aligned": True},
        },
        {
            "event": "intent_state",
            "active_objective": "compute",
            "result": {"status": "completed", "aligned": True},
        },
        {
            "event": "intent_state",
            "active_objective": "compute",
            "result": {"status": "failed", "aligned": False},
            "correction": "execution failure",
        },
    ]
    t = summarize(events, "compute")
    assert t.attempts == 3
    assert t.aligned == 2
    assert t.failed == 1
    assert t.corrections == 1
    assert t.alignment_rate == 2 / 3
    assert t.evidence_status == "SUPPORTED"
