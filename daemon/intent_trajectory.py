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
