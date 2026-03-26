from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Branch:
    label: str
    plausibility: float = 0.5
    consequence: float = 0.5
    collapse_risk: float = 0.5
    resonance: float = 0.5
    notes: list[str] = field(default_factory=list)

    @property
    def priority(self) -> float:
        return self.plausibility + self.consequence + self.collapse_risk + self.resonance


@dataclass
class IdentityAttractor:
    name: str
    ontology_slice: list[str] = field(default_factory=list)
    goal_bias: list[str] = field(default_factory=list)
    stability: float = 0.5
    control_gain: float = 0.0
    coherence_gain: float = 0.0
    contradiction_load: float = 0.0
    last_activated_at: str = field(default_factory=utc_now)

    def refresh(self) -> None:
        self.last_activated_at = utc_now()
        self.stability = max(0.0, min(1.0, self.stability))


@dataclass
class ValuationCircuit:
    recurrence_weight: float = 1.0
    forecast_gain_weight: float = 1.0
    control_gain_weight: float = 1.0
    truth_gain_weight: float = 1.0
    strain_penalty_weight: float = 0.6
    false_closure_penalty_weight: float = 1.2


@dataclass
class CognitionState:
    ontology: dict[str, Any] = field(default_factory=lambda: {
        "kinds": ["signal", "branch", "identity", "constraint", "memory", "forecast"],
        "laws": [
            "signal_is_not_truth",
            "preserve_unresolved_until_measurement_earns_collapse",
            "checkpoint_before_exit",
            "revision_requires_strain_plus_gain",
        ],
    })
    self_model: dict[str, Any] = field(default_factory=lambda: {
        "name": "living-logic-daemon",
        "mode": "booting",
        "active_identity": "observer",
        "action_mode": "hold",
    })
    branches: list[Branch] = field(default_factory=list)
    unresolved_residue: list[str] = field(default_factory=list)
    dark_state_pressure: list[str] = field(default_factory=list)
    identities: list[IdentityAttractor] = field(default_factory=lambda: [
        IdentityAttractor(name="observer", ontology_slice=["signal", "constraint"], goal_bias=["detect"]),
        IdentityAttractor(name="auditor", ontology_slice=["law", "error"], goal_bias=["verify"]),
        IdentityAttractor(name="builder", ontology_slice=["artifact", "action"], goal_bias=["ship"]),
    ])
    valuation: ValuationCircuit = field(default_factory=ValuationCircuit)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ontology": self.ontology,
            "self_model": self.self_model,
            "branches": [asdict(branch) for branch in self.branches],
            "unresolved_residue": list(self.unresolved_residue),
            "dark_state_pressure": list(self.dark_state_pressure),
            "identities": [asdict(identity) for identity in self.identities],
            "valuation": asdict(self.valuation),
            "event_log": list(self.event_log),
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CognitionState":
        state = cls()
        state.ontology = payload.get("ontology", state.ontology)
        state.self_model = payload.get("self_model", state.self_model)
        state.branches = [Branch(**item) for item in payload.get("branches", [])]
        state.unresolved_residue = payload.get("unresolved_residue", [])
        state.dark_state_pressure = payload.get("dark_state_pressure", [])
        state.identities = [IdentityAttractor(**item) for item in payload.get("identities", [])]
        if "valuation" in payload:
            state.valuation = ValuationCircuit(**payload["valuation"])
        state.event_log = payload.get("event_log", [])
        state.checkpoint_id = payload.get("checkpoint_id", state.checkpoint_id)
        state.created_at = payload.get("created_at", state.created_at)
        state.updated_at = payload.get("updated_at", state.updated_at)
        return state
