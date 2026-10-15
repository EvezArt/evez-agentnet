"""Intent-state controller for governed EVEZ cognition.

The controller models only intent inferred from observable interaction signals.
It never treats inferred intent as ground truth and never claims access to hidden
mental state.

Pipeline:
    signal -> hypothesis -> action bias -> result -> correction -> update

The state is deterministic and hashable so it can be emitted into the spine.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable


class IntentStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IntentSignal:
    """Observable interaction evidence used to update an intent hypothesis."""

    kind: str
    value: str
    weight: float = 1.0
    source: str = "interaction"


@dataclass(frozen=True)
class IntentHypothesis:
    objective: str
    signals: tuple[IntentSignal, ...] = ()
    status: IntentStatus = IntentStatus.UNKNOWN
    score: float = 0.0

    @property
    def confidence(self) -> float:
        return max(0.0, min(1.0, self.score))


@dataclass
class UserIntentState:
    """Runtime control state derived from observable interaction signals."""

    explicit_objective: str | None = None
    hypotheses: dict[str, IntentHypothesis] = field(default_factory=dict)
    active_objective: str | None = None
    correction_count: int = 0
    successful_alignment_count: int = 0
    failed_alignment_count: int = 0
    revision: int = 0

    def observe(
        self,
        objective: str,
        signals: Iterable[IntentSignal],
    ) -> IntentHypothesis:
        """Add/update an intent hypothesis from observable signals."""

        incoming = tuple(signals)
        previous = self.hypotheses.get(objective)
        score = sum(max(-1.0, min(1.0, s.weight)) for s in incoming)

        if previous:
            score += previous.score
            incoming = previous.signals + incoming

        score = max(-10.0, min(10.0, score))
        status = (
            IntentStatus.SUPPORTED
            if score > 0
            else IntentStatus.CONTRADICTED
            if score < 0
            else IntentStatus.UNKNOWN
        )

        hypothesis = IntentHypothesis(
            objective=objective,
            signals=incoming,
            status=status,
            score=score,
        )
        self.hypotheses[objective] = hypothesis
        self._select_active()
        self.revision += 1
        return hypothesis

    def set_explicit_objective(self, objective: str) -> None:
        """Explicit instructions have authority over inferred hypotheses."""

        previous_active = self.active_objective
        self.explicit_objective = objective

        if previous_active and previous_active != objective:
            previous = self.hypotheses.get(previous_active)
            if previous:
                self.hypotheses[previous_active] = IntentHypothesis(
                    objective=previous.objective,
                    signals=previous.signals + (
                        IntentSignal(
                            kind="explicit_authority",
                            value=f"explicit objective replaced {previous_active}",
                            weight=-1.0,
                            source="user",
                        ),
                    ),
                    status=IntentStatus.CONTRADICTED,
                    score=min(-1.0, previous.score - 1.0),
                )

        target = self.hypotheses.get(objective)
        target_signals = (target.signals if target else ()) + (
            IntentSignal(
                kind="explicit_authority",
                value=f"user explicitly selected {objective}",
                weight=2.0,
                source="user",
            ),
        )
        self.hypotheses[objective] = IntentHypothesis(
            objective=objective,
            signals=target_signals,
            status=IntentStatus.SUPPORTED,
            score=max(1.0, (target.score if target else 0.0) + 2.0),
        )
        self.active_objective = objective
        self.revision += 1

    def record_result(self, aligned: bool) -> None:
        """Feed the result of an action back into the controller."""

        if aligned:
            self.successful_alignment_count += 1
        else:
            self.failed_alignment_count += 1
        self.revision += 1

    def apply_correction(self, objective: str, explanation: str = "") -> None:
        """Register a correction and positively support the corrected objective."""

        self.correction_count += 1

        if self.active_objective and self.active_objective != objective:
            previous = self.hypotheses.get(self.active_objective)
            if previous:
                self.hypotheses[self.active_objective] = IntentHypothesis(
                    objective=previous.objective,
                    signals=previous.signals + (
                        IntentSignal(
                            kind="user_correction",
                            value=explanation or "user rejected prior inference",
                            weight=-1.0,
                            source="user",
                        ),
                    ),
                    status=IntentStatus.CONTRADICTED,
                    score=min(-1.0, previous.score - 1.0),
                )

        self.observe(
            objective,
            (
                IntentSignal(
                    kind="user_correction",
                    value=explanation or "user specified corrected objective",
                    weight=2.0,
                    source="user",
                ),
            ),
        )
        self.active_objective = objective
        self.revision += 1

    def _select_active(self) -> None:
        if self.explicit_objective:
            self.active_objective = self.explicit_objective
            return

        candidates = [
            h for h in self.hypotheses.values()
            if h.status in (IntentStatus.SUPPORTED, IntentStatus.UNKNOWN)
        ]

        self.active_objective = (
            max(
                candidates,
                key=lambda h: (h.score, len(h.signals), h.objective),
            ).objective
            if candidates
            else None
        )

    def snapshot(self) -> dict:
        """Return canonical, JSON-safe state for a spine event."""

        payload = asdict(self)
        payload["hypotheses"] = {
            key: asdict(value)
            for key, value in sorted(self.hypotheses.items())
        }
        return payload

    def canonical_bytes(self) -> bytes:
        """Canonical representation used for deterministic hashing."""

        return json.dumps(
            self.snapshot(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def state_hash(self) -> str:
        return hashlib.sha256(
            b"EVEZ/INTENT-STATE/v1\x00" + self.canonical_bytes()
        ).hexdigest()


def _candidate_is_negated(text: str, candidate: str) -> bool:
    """Detect simple local negation immediately preceding a candidate mention."""

    lowered = text.lower()
    target = candidate.lower()
    start = lowered.find(target)
    if start < 0:
        return False

    prefix = lowered[max(0, start - 32):start]
    negators = ("not ", "don't ", "dont ", "do not ", "never ", "no ")
    return any(prefix.rstrip().endswith(negator.rstrip()) for negator in negators)


def infer_intent(
    signals: Iterable[IntentSignal],
    candidates: Iterable[str],
) -> IntentHypothesis | None:
    """Select the strongest candidate from observable evidence only."""

    signal_list = tuple(signals)
    scored: list[IntentHypothesis] = []

    for candidate in candidates:
        relevant: list[IntentSignal] = []
        for signal in signal_list:
            value = signal.value.lower()
            kind = signal.kind.lower()
            if candidate.lower() not in value and candidate.lower() not in kind:
                continue
            if _candidate_is_negated(signal.value, candidate):
                relevant.append(
                    IntentSignal(
                        kind=signal.kind,
                        value=signal.value,
                        weight=-abs(signal.weight),
                        source=signal.source,
                    )
                )
            else:
                relevant.append(signal)

        relevant = tuple(relevant)
        score = sum(max(-1.0, min(1.0, s.weight)) for s in relevant)
        if score != 0:
            scored.append(
                IntentHypothesis(
                    objective=candidate,
                    signals=relevant,
                    status=(
                        IntentStatus.SUPPORTED
                        if score > 0
                        else IntentStatus.CONTRADICTED
                    ),
                    score=score,
                )
            )

    return (
        max(scored, key=lambda h: (h.score, len(h.signals), h.objective))
        if scored
        else None
    )
