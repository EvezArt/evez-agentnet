from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ORS_FORCE_CHANNELS = {
    "because": "EVID",
    "data": "EVID",
    "source": "EVID",
    "obvious": "FLU",
    "feels": "AFW",
    "always": "FAM",
    "everyone": "SOC",
    "must": "GOAL",
}


@dataclass
class ORSAssessment:
    force_channels: list[str]
    rival_required: bool
    acquisition_needed: bool
    state_locked_risk: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "force_channels": self.force_channels,
            "rival_required": self.rival_required,
            "acquisition_needed": self.acquisition_needed,
            "state_locked_risk": self.state_locked_risk,
        }


class ORSBridge:
    """Minimal bridge into the ORS doctrine already present in the repo.

    It does not parse the whole ORS spec. It tags inputs with enough structure
    to bias the daemon toward acquisition and away from premature closure.
    """

    def assess(self, text: str) -> ORSAssessment:
        lower = text.lower()
        channels = sorted({code for token, code in ORS_FORCE_CHANNELS.items() if token in lower})
        rival_required = True
        acquisition_needed = not any(token in lower for token in ["source", "observed", "measured", "evidence"])
        state_locked_risk = 0.2
        if any(token in lower for token in ["obvious", "certain", "always", "never"]):
            state_locked_risk += 0.35
        if acquisition_needed:
            state_locked_risk += 0.2
        if "because" not in lower:
            state_locked_risk += 0.1
        return ORSAssessment(
            force_channels=channels or ["UNDECLARED"],
            rival_required=rival_required,
            acquisition_needed=acquisition_needed,
            state_locked_risk=min(state_locked_risk, 1.0),
        )
