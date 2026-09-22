"""Immutable action/outcome records for intent-guided execution.

The ledger records an observed execution sequence:
    intent before -> selected action -> result -> intent after

It does not claim proven causality. association_status explicitly marks the
record as an observed sequence so downstream learning does not silently turn
correlation into causal certainty.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ActionOutcome:
    """Canonical causal-trace record for one executed action."""

    schema_version: int
    task_id: str
    objective: str
    intent_state_before: str
    action: str
    execution_path: str
    result_status: str
    aligned: bool | None
    result_digest: str | None
    result_length: int | None
    correction: str | None
    intent_state_after: str
    association_status: str = "OBSERVED_SEQUENCE"

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.snapshot(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def record_hash(self) -> str:
        return hashlib.sha256(
            b"EVEZ/ACTION-OUTCOME/v1\x00" + self.canonical_bytes()
        ).hexdigest()


def digest_result(result: Any) -> str | None:
    """Hash the result without retaining its content in the causal record."""

    if result is None:
        return None

    if isinstance(result, str):
        payload = result.encode("utf-8")
    else:
        payload = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

    return hashlib.sha256(
        b"EVEZ/ACTION-RESULT/v1\x00" + payload
    ).hexdigest()


def build_action_outcome(
    *,
    task_id: str,
    objective: str,
    intent_state_before: str,
    action: str,
    execution_path: str,
    result_status: str,
    aligned: bool | None,
    result: Any,
    correction: str | None,
    intent_state_after: str,
) -> ActionOutcome:
    """Construct one immutable action/outcome record."""

    if isinstance(result, str):
        result_length = len(result)
    elif result is None:
        result_length = None
    else:
        result_length = len(json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ))

    return ActionOutcome(
        schema_version=1,
        task_id=str(task_id),
        objective=objective,
        intent_state_before=intent_state_before,
        action=action,
        execution_path=execution_path,
        result_status=result_status,
        aligned=aligned,
        result_digest=digest_result(result),
        result_length=result_length,
        correction=correction,
        intent_state_after=intent_state_after,
    )


def validate_linkage(record: Mapping[str, Any]) -> bool:
    """Validate the non-empty state links of a serialized record."""

    before = record.get("intent_state_before")
    after = record.get("intent_state_after")
    return (
        isinstance(before, str)
        and len(before) == 64
        and isinstance(after, str)
        and len(after) == 64
        and bool(record.get("task_id"))
        and bool(record.get("action"))
        and bool(record.get("execution_path"))
    )
