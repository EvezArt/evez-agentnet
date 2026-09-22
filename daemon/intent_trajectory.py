"""Auditable trajectory memory for intent-guided execution.

This layer reads only committed spine events. It summarizes prior outcomes into
routing evidence without rewriting historical events.

Historical outcomes are evidence, not truth: a small sample yields UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from . import spine
from .intent_state import IntentSignal


@dataclass(frozen=True)
class IntentTrajectory:
    objective: str
    attempts: int
    aligned: int
    failed: int
    corrections: int
    alignment_rate: float | None
    evidence_status: str

    def signal(self) -> IntentSignal:
        if self.alignment_rate is None:
            weight = 0.0
        elif self.alignment_rate >= 0.8:
            weight = 0.5
        elif self.alignment_rate <= 0.4:
            weight = -0.5
        else:
            weight = 0.0

        return IntentSignal(
            kind="historical_trajectory",
            value=(
                f"{self.objective}: attempts={self.attempts}, "
                f"aligned={self.aligned}, failed={self.failed}, "
                f"corrections={self.corrections}"
            ),
            weight=weight,
            source="spine",
        )



@dataclass(frozen=True)
class ActionTrajectory:
    """Outcome evidence scoped to one observed execution path."""

    objective: str
    action: str
    execution_path: str
    attempts: int
    aligned: int
    failed: int
    corrections: int
    alignment_rate: float | None
    evidence_status: str

    def signal(self) -> IntentSignal:
        if self.alignment_rate is None:
            weight = 0.0
        elif self.alignment_rate >= 0.8:
            weight = 0.5
        elif self.alignment_rate <= 0.4:
            weight = -0.5
        else:
            weight = 0.0

        return IntentSignal(
            kind="historical_action_trajectory",
            value=(
                f"{self.objective}: action={self.action}, "
                f"path={self.execution_path}, attempts={self.attempts}, "
                f"aligned={self.aligned}, failed={self.failed}, "
                f"corrections={self.corrections}"
            ),
            weight=weight,
            source="spine",
        )


def summarize(
    events: Iterable[Mapping],
    objective: str,
    *,
    minimum_samples: int = 3,
) -> IntentTrajectory:
    attempts = aligned = failed = corrections = 0

    for event in events:
        if event.get("event") != "intent_state":
            continue
        if event.get("active_objective") != objective:
            continue

        result = event.get("result") or {}
        status = result.get("status")

        if status in {"completed", "failed"}:
            attempts += 1

        if result.get("aligned") is True:
            aligned += 1
        elif result.get("aligned") is False:
            failed += 1

        if event.get("correction") is not None:
            corrections += 1

    if attempts < minimum_samples:
        return IntentTrajectory(
            objective=objective,
            attempts=attempts,
            aligned=aligned,
            failed=failed,
            corrections=corrections,
            alignment_rate=None,
            evidence_status="UNKNOWN",
        )

    rate = aligned / attempts if attempts else None
    return IntentTrajectory(
        objective=objective,
        attempts=attempts,
        aligned=aligned,
        failed=failed,
        corrections=corrections,
        alignment_rate=rate,
        evidence_status="SUPPORTED" if rate is not None else "UNKNOWN",
    )


def recent(objective: str, *, limit: int = 100) -> IntentTrajectory:
    return summarize(spine.tail(limit), objective)


def summarize_action(
    events: Iterable[Mapping],
    objective: str,
    *,
    action: str | None = None,
    execution_path: str | None = None,
    minimum_samples: int = 3,
) -> ActionTrajectory:
    """Summarize observed action outcomes without asserting causality."""

    attempts = aligned = failed = corrections = 0
    selected_action = action or "UNKNOWN"
    selected_path = execution_path or "UNKNOWN"

    for event in events:
        if event.get("event") != "action_outcome":
            continue
        if event.get("objective") != objective:
            continue
        if action is not None and event.get("action") != action:
            continue
        if execution_path is not None and event.get("execution_path") != execution_path:
            continue

        if selected_action == "UNKNOWN":
            selected_action = event.get("action") or "UNKNOWN"
        if selected_path == "UNKNOWN":
            selected_path = event.get("execution_path") or "UNKNOWN"

        status = event.get("result_status")
        if status in {"completed", "failed"}:
            attempts += 1

        if event.get("aligned") is True:
            aligned += 1
        elif event.get("aligned") is False:
            failed += 1

        if event.get("correction") is not None:
            corrections += 1

    if attempts < minimum_samples:
        rate = None
        evidence_status = "UNKNOWN"
    else:
        rate = aligned / attempts if attempts else None
        evidence_status = "SUPPORTED" if rate is not None else "UNKNOWN"

    return ActionTrajectory(
        objective=objective,
        action=selected_action,
        execution_path=selected_path,
        attempts=attempts,
        aligned=aligned,
        failed=failed,
        corrections=corrections,
        alignment_rate=rate,
        evidence_status=evidence_status,
    )


def recent_action(
    objective: str,
    *,
    action: str | None = None,
    execution_path: str | None = None,
    limit: int = 100,
) -> ActionTrajectory:
    """Return recent action-specific evidence from the committed spine."""

    return summarize_action(
        spine.tail(limit),
        objective,
        action=action,
        execution_path=execution_path,
    )
