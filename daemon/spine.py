"""Append-only, hash-chained event spine for EVEZ AgentNet.

Every appended event receives:
    prev_hash: hash of the previous canonical event
    event_hash: SHA-256(domain || prev_hash || canonical_event)

Intent-state commits use the same spine so inferred user intent becomes an
auditable controller input rather than an invisible prompt-side heuristic.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .action_outcome import ActionOutcome
from .intent_state import UserIntentState

try:
    import fcntl
except ImportError:  # pragma: no cover - Linux is the supported daemon target.
    fcntl = None

SPINE_PATH = Path(os.environ.get("DAEMON_SPINE", "daemon/spine.jsonl"))
_HASH_DOMAIN = b"EVEZ/SPINE/EVENT/v1\x00"
_GENESIS = "0" * 64


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _last_event_hash(handle) -> str:
    """Read the chain head from the already-locked file descriptor."""
    handle.seek(0)
    last_hash = _GENESIS

    for line in handle:
        if not line.strip():
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "spine contains invalid JSON; refusing to append"
            ) from exc

        value = event.get("event_hash")
        if not isinstance(value, str) or len(value) != 64:
            raise RuntimeError(
                "spine contains an invalid event_hash; refusing to append"
            )

        last_hash = value

    return last_hash


def verify_event(event: Mapping[str, Any]) -> bool:
    """Verify one event against its stored previous hash and event hash."""

    stored = event.get("event_hash")
    previous = event.get("prev_hash")

    if not isinstance(stored, str) or not isinstance(previous, str):
        return False

    try:
        previous_bytes = bytes.fromhex(previous)
    except ValueError:
        return False

    body = dict(event)
    body.pop("event_hash", None)

    digest = hashlib.sha256(
        _HASH_DOMAIN
        + previous_bytes
        + _canonical_bytes(body)
    ).hexdigest()

    return digest == stored


def _append_unlocked(entry: dict[str, Any]) -> dict[str, Any]:
    SPINE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with SPINE_PATH.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            # The same locked descriptor is used for both head calculation and
            # append. This prevents a second descriptor from observing a
            # different chain head between read and write.
            previous_hash = _last_event_hash(handle)
            handle.seek(0, os.SEEK_END)

            entry["prev_hash"] = previous_hash
            entry.pop("event_hash", None)
            entry["event_hash"] = hashlib.sha256(
                _HASH_DOMAIN
                + bytes.fromhex(previous_hash)
                + _canonical_bytes(entry)
            ).hexdigest()

            handle.write(
                json.dumps(
                    entry,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return entry


def append(event_type: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Append one hash-chained event and return the committed entry."""

    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **dict(data),
    }

    return _append_unlocked(entry)


def append_action_outcome(record: ActionOutcome) -> dict[str, Any]:
    """Commit one immutable action/outcome record into the spine."""

    return append(
        "action_outcome",
        {
            "action_outcome_version": record.schema_version,
            "task_id": record.task_id,
            "objective": record.objective,
            "intent_state_before": record.intent_state_before,
            "intent_event_before": record.intent_event_before,
            "action": record.action,
            "execution_path": record.execution_path,
            "result_status": record.result_status,
            "aligned": record.aligned,
            "result_digest": record.result_digest,
            "result_length": record.result_length,
            "correction": record.correction,
            "intent_state_after": record.intent_state_after,
            "intent_event_after": record.intent_event_after,
            "association_status": record.association_status,
            "record_hash": record.record_hash(),
        },
    )


def append_intent_state(
    state: UserIntentState,
    *,
    action: str | None = None,
    result: Mapping[str, Any] | None = None,
    correction: str | None = None,
) -> dict[str, Any]:
    """Commit the current intent controller state into the event spine."""

    return append(
        "intent_state",
        {
            "intent_state_version": 1,
            "controller_revision": state.revision,
            "active_objective": state.active_objective,
            "action": action,
            "result": dict(result) if result is not None else None,
            "correction": correction,
            "state": state.snapshot(),
            "state_hash": state.state_hash(),
        },
    )


def append_presentation(
    *,
    artifact_hash: str,
    watermark_id: str,
    device: str,
    source: str = "LOCAL",
    association: str = "PRESENTATION_ONLY",
) -> dict[str, Any]:
    """Record presentation metadata without changing canonical artifact bytes.

    The spine records the observed presentation relationship. It does not
    assert that presentation caused, created, or altered the artifact.
    """

    return append(
        "presentation",
        {
            "presentation_version": 1,
            "artifact_hash": artifact_hash,
            "watermark_id": watermark_id,
            "device": device,
            "source": source,
            "association": association,
            "association_status": "OBSERVED_SEQUENCE",
        },
    )


def verify_chain() -> tuple[bool, int, str]:
    """Verify the entire local spine.

    Returns:
        (valid, events_checked, last_hash)
    """

    if not SPINE_PATH.exists():
        return True, 0, _GENESIS

    previous = _GENESIS
    checked = 0

    with SPINE_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return False, checked, previous

            if event.get("prev_hash") != previous:
                return False, checked, previous

            if not verify_event(event):
                return False, checked, previous

            previous = event["event_hash"]
            checked += 1

    return True, checked, previous


def tail(n: int = 20) -> list[dict[str, Any]]:
    if not SPINE_PATH.exists() or n <= 0:
        return []

    lines = SPINE_PATH.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []

    for line in lines[-n:]:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            out.append(event)

    return out


def count() -> int:
    if not SPINE_PATH.exists():
        return 0

    with SPINE_PATH.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())
