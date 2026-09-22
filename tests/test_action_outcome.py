from daemon import spine
from daemon.action_outcome import build_action_outcome, validate_linkage


def test_action_outcome_links_intent_states_and_hashes_result():
    before = "1" * 64
    after = "2" * 64
    record = build_action_outcome(
        task_id="42",
        objective="execute_task",
        intent_state_before=before,
        intent_event_before="3" * 64,
        action="router.complete",
        execution_path="router",
        result_status="completed",
        aligned=True,
        result="result",
        correction=None,
        intent_state_after=after,
        intent_event_after="4" * 64,
    )

    assert validate_linkage(record.snapshot()) is True
    assert record.result_digest is not None
    assert len(record.result_digest) == 64
    assert len(record.record_hash()) == 64


def test_action_outcome_is_committed_to_spine(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    record = build_action_outcome(
        task_id="7",
        objective="build",
        intent_state_before="a" * 64,
        intent_event_before="c" * 64,
        action="builder.handle_build_task",
        execution_path="builder",
        result_status="failed",
        aligned=False,
        result="boom",
        correction="execution failure",
        intent_state_after="b" * 64,
        intent_event_after="d" * 64,
    )

    entry = spine.append_action_outcome(record)

    assert entry["event"] == "action_outcome"
    assert entry["record_hash"] == record.record_hash()
    assert entry["association_status"] == "OBSERVED_SEQUENCE"
    assert spine.verify_event(entry)

    valid, checked, _ = spine.verify_chain()
    assert valid is True
    assert checked == 1
