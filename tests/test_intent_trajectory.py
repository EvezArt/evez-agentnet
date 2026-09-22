from daemon.intent_trajectory import summarize, summarize_action


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


def test_action_trajectory_stays_unknown_until_three_observations():
    events = [
        {
            "event": "action_outcome",
            "objective": "compute",
            "action": "router.complete",
            "execution_path": "router",
            "result_status": "completed",
            "aligned": True,
        },
    ]

    t = summarize_action(
        events,
        "compute",
        action="router.complete",
        execution_path="router",
    )

    assert t.evidence_status == "UNKNOWN"
    assert t.alignment_rate is None


def test_action_trajectory_is_scoped_to_execution_path():
    events = [
        {
            "event": "action_outcome",
            "objective": "compute",
            "action": "router.complete",
            "execution_path": "router",
            "result_status": "completed",
            "aligned": True,
        },
        {
            "event": "action_outcome",
            "objective": "compute",
            "action": "router.complete",
            "execution_path": "router",
            "result_status": "completed",
            "aligned": True,
        },
        {
            "event": "action_outcome",
            "objective": "compute",
            "action": "builder.handle_build_task",
            "execution_path": "builder",
            "result_status": "completed",
            "aligned": True,
        },
    ]

    t = summarize_action(
        events,
        "compute",
        action="router.complete",
        execution_path="router",
    )

    assert t.attempts == 2
    assert t.aligned == 2
    assert t.evidence_status == "UNKNOWN"

    all_paths = summarize_action(events, "compute", minimum_samples=3)
    assert all_paths.attempts == 3
    assert all_paths.evidence_status == "SUPPORTED"
