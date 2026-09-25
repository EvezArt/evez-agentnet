from __future__ import annotations

import json
import pytest

from daemon import spine
from daemon.intent_state import IntentSignal, UserIntentState


def test_append_creates_hash_chain(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    first = spine.append("first", {"value": 1})
    second = spine.append("second", {"value": 2})

    assert first["prev_hash"] == "0" * 64
    assert second["prev_hash"] == first["event_hash"]
    assert spine.verify_event(first)
    assert spine.verify_event(second)

    valid, checked, last_hash = spine.verify_chain()
    assert valid is True
    assert checked == 2
    assert last_hash == second["event_hash"]


def test_tampering_breaks_chain(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    spine.append("first", {"value": 1})
    spine.append("second", {"value": 2})

    lines = path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["value"] = 999
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    valid, checked, _ = spine.verify_chain()
    assert valid is False
    assert checked == 0


def test_intent_state_is_committed_to_spine(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    state = UserIntentState()
    state.observe(
        "compute",
        [IntentSignal("trajectory", "compute the next state", 1.0)],
    )

    entry = spine.append_intent_state(
        state,
        action="compute_next_state",
        result={"aligned": True},
    )

    assert entry["event"] == "intent_state"
    assert entry["active_objective"] == "compute"
    assert entry["state_hash"] == state.state_hash()
    assert spine.verify_event(entry)

    valid, checked, _ = spine.verify_chain()
    assert valid is True
    assert checked == 1


def test_presentation_is_committed_without_claiming_causality(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    entry = spine.append_presentation(
        artifact_hash="a" * 64,
        watermark_id="wm-123",
        device="EVEZ-POCKET",
    )

    assert entry["event"] == "presentation"
    assert entry["artifact_hash"] == "a" * 64
    assert entry["association"] == "PRESENTATION_ONLY"
    assert entry["association_status"] == "OBSERVED_SEQUENCE"
    assert "causal" not in entry

    valid, checked, _ = spine.verify_chain()
    assert valid is True
    assert checked == 1


def test_removing_an_event_breaks_prev_hash_link(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    spine.append("first", {"value": 1})
    spine.append("second", {"value": 2})
    spine.append("third", {"value": 3})

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")

    valid, checked, _ = spine.verify_chain()
    assert valid is False
    assert checked == 0


def test_corrupt_tail_refuses_append(tmp_path, monkeypatch):
    path = tmp_path / "spine.jsonl"
    monkeypatch.setattr(spine, "SPINE_PATH", path)

    spine.append("first", {"value": 1})
    path.write_text(path.read_text(encoding="utf-8") + "{broken-json\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid JSON"):
        spine.append("second", {"value": 2})
