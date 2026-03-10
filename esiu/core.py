#!/usr/bin/env python3
"""ESIU - Event Source Investigation Unit.

Defensive event investigation primitives:
- append-only event ingestion
- backtrace / forward-trace around suspicious events
- policy-based isolation recommendations with human approval gating
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Event:
    """Security-relevant event."""

    kind: str
    source: str
    actor: str
    subject: str
    severity: int
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.event_id:
            payload = f"{self.kind}|{self.source}|{self.actor}|{self.subject}|{self.timestamp}"
            self.event_id = hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class Investigation:
    root_event: Event
    backtrace: list[Event] = field(default_factory=list)
    forward_impact: list[Event] = field(default_factory=list)
    verdict: str = "PENDING"
    action_taken: str = "NONE"


class ProvenanceGraph:
    """Append-only event graph supporting causal neighborhood traces."""

    def __init__(self, store_path: str = "esiu_events.jsonl") -> None:
        self.store_path = Path(store_path)
        self.events: list[Event] = []
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        with open(self.store_path) as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                self.events.append(Event(**data))

    def ingest(self, event: Event) -> str:
        self.events.append(event)
        with open(self.store_path, "a") as f:
            f.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event.event_id

    def backtrace(self, event: Event, window_seconds: int = 300) -> list[Event]:
        """Find earlier events from same source or actor."""
        root_time = datetime.fromisoformat(event.timestamp)
        results = []
        for candidate in self.events:
            if candidate.event_id == event.event_id:
                continue
            candidate_time = datetime.fromisoformat(candidate.timestamp)
            delta = (root_time - candidate_time).total_seconds()
            if 0 < delta <= window_seconds and (
                candidate.source == event.source or candidate.actor == event.actor
            ):
                results.append(candidate)
        return sorted(results, key=lambda x: x.timestamp)

    def forward_trace(self, event: Event, window_seconds: int = 300) -> list[Event]:
        """Find later events from same source or actor."""
        root_time = datetime.fromisoformat(event.timestamp)
        results = []
        for candidate in self.events:
            if candidate.event_id == event.event_id:
                continue
            candidate_time = datetime.fromisoformat(candidate.timestamp)
            delta = (candidate_time - root_time).total_seconds()
            if 0 < delta <= window_seconds and (
                candidate.source == event.source or candidate.actor == event.actor
            ):
                results.append(candidate)
        return sorted(results, key=lambda x: x.timestamp)


class IsolationPolicy:
    """Defensive policy mapping severity to constrained actions."""

    THRESHOLDS = {
        "OBSERVE": (0, 40),
        "RESTRICT": (40, 65),
        "QUARANTINE": (65, 85),
        "FREEZE": (85, 101),
    }

    def evaluate(self, event: Event, backtrace: list[Event]) -> dict[str, Any]:
        repeat_count = sum(1 for prior in backtrace if prior.actor == event.actor)
        adjusted = min(100, event.severity + (repeat_count * 5))

        action = "OBSERVE"
        for level, (low, high) in self.THRESHOLDS.items():
            if low <= adjusted < high:
                action = level
                break

        requires_human = action in {"QUARANTINE", "FREEZE"}
        return {
            "action": action,
            "adjusted_severity": adjusted,
            "repeat_count": repeat_count,
            "requires_human": requires_human,
            "reason": f"severity={adjusted}, repeats={repeat_count}",
        }


class ESIU:
    """Ingest -> trace -> policy -> append case log."""

    def __init__(self, store_path: str = "esiu_events.jsonl", case_log_path: str = "esiu_cases.jsonl"):
        self.graph = ProvenanceGraph(store_path)
        self.policy = IsolationPolicy()
        self.case_log = Path(case_log_path)

    def investigate(self, event: Event) -> Investigation:
        self.graph.ingest(event)
        back = self.graph.backtrace(event)
        forward = self.graph.forward_trace(event)
        decision = self.policy.evaluate(event, back)

        inv = Investigation(
            root_event=event,
            backtrace=back,
            forward_impact=forward,
            verdict=decision["action"],
            action_taken="QUEUED_FOR_HUMAN" if decision["requires_human"] else decision["action"],
        )

        case = {
            "case_id": event.event_id,
            "timestamp": event.timestamp,
            "verdict": inv.verdict,
            "action": inv.action_taken,
            "backtrace_n": len(back),
            "forward_n": len(forward),
            "decision": decision,
        }
        with open(self.case_log, "a") as f:
            f.write(json.dumps(case, sort_keys=True) + "\n")

        return inv
