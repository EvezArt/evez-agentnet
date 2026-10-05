from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any
import hashlib
import json

STATES = ("UNKNOWN", "OBSERVED", "EXECUTABLE", "TESTED", "REPRODUCED", "VALIDATED", "PROMOTED")

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class Observation:
    source: str
    subject: str
    value: Any
    observed_at: str
    evidence_id: str = ""

    def as_record(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = "evez.observation.v1"
        data["evidence_id"] = self.evidence_id or "obs-" + digest(data)[:20]
        return data

@dataclass(frozen=True)
class Capability:
    capability_id: str
    name: str
    repository: str
    state: str = "UNKNOWN"
    confidence: str = "UNKNOWN"
    interfaces: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"invalid capability state: {self.state}")

@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    objective: str
    inputs: dict[str, Any]
    expected_invariants: list[str]
    authority: int = 2

@dataclass(frozen=True)
class Receipt:
    action_id: str
    status: str
    artifacts: list[str]
    parent_event_hash: str
    observed_result: dict[str, Any]
