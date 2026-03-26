from __future__ import annotations

"""Shared governance thresholds for cognition-first entrypoints."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GovernancePolicy:
    unresolved_threshold: int = 10
    predictor_entropy_threshold: float = 1.2
    ship_action_modes: tuple[str, ...] = ("construct", "prepare")
    proof_spine_tail: int = 25
    dashboard_spine_tail: int = 16
    queue_draft_limit: int = 3

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_POLICY = GovernancePolicy()
