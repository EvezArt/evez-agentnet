from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import Branch, CognitionState, IdentityAttractor, utc_now


class ExecutiveArbiter:
    """Selects the next executive identity and action bias.

    This is the closest thing to the scaffold's frontal controller.
    It does not try to be mystical. It scores urgency, uncertainty,
    contradiction load, and builder pressure, then picks the least bad move.
    """

    def choose(self, state: CognitionState, branch: Branch | None) -> dict[str, Any]:
        if branch is None:
            return {
                "identity": state.self_model.get("active_identity", "observer"),
                "action_mode": "hold",
                "reason": "no_live_branch",
                "at": utc_now(),
            }

        if branch.collapse_risk >= 0.7:
            identity = "auditor"
            action_mode = "evidence_seek"
            reason = "high_false_closure_risk"
        elif branch.consequence >= 0.65 and "build" in " ".join(branch.notes).lower():
            identity = "builder"
            action_mode = "construct"
            reason = "high_consequence_builder_branch"
        elif branch.priority >= 2.4:
            identity = "builder"
            action_mode = "prepare"
            reason = "high_priority_branch"
        else:
            identity = "observer"
            action_mode = "watch"
            reason = "monitor_branch"

        return {
            "identity": identity,
            "action_mode": action_mode,
            "reason": reason,
            "branch": asdict(branch),
            "at": utc_now(),
        }

    def apply(self, state: CognitionState, plan: dict[str, Any]) -> IdentityAttractor:
        target = next(item for item in state.identities if item.name == plan["identity"])
        target.refresh()
        state.self_model["active_identity"] = target.name
        state.self_model["action_mode"] = plan["action_mode"]
        return target
