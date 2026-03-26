from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .buildloop import BuildLoop
from .checkpoint import CheckpointStore
from .executive import ExecutiveArbiter
from .lineage import LineageEvent, LineageStore
from .models import Branch, CognitionState, IdentityAttractor, utc_now
from .ors_bridge import ORSBridge


class LivingLogicDaemon:
    """Restartable cognition kernel wired for audit, branch preservation, and boot continuity."""

    def __init__(self, store: CheckpointStore) -> None:
        self.store = store
        self.state = store.load_latest() or CognitionState()
        self.state.self_model["mode"] = "running"
        self.executive = ExecutiveArbiter()
        self.ors = ORSBridge()
        self.lineage = LineageStore(store.root)
        self.buildloop = BuildLoop(store.root)
        self.last_hash = "GENESIS"
        self._log("boot", {"checkpoint_id": self.state.checkpoint_id})

    def _log(self, kind: str, payload: dict[str, Any]) -> None:
        event = {"at": utc_now(), "kind": kind, "payload": payload}
        self.state.event_log.append(event)
        self.last_hash = self.lineage.append(LineageEvent(kind=kind, payload=event, parent_hash=self.last_hash))

    def _score_branch(self, label: str, text: str) -> Branch:
        lower = text.lower()
        ors = self.ors.assess(text)
        plausibility = 0.35 + 0.15 * ("because" in lower or "therefore" in lower)
        consequence = 0.35 + 0.15 * any(token in lower for token in ["must", "risk", "ship", "deploy", "urgent"])
        collapse_risk = 0.4 + 0.2 * any(token in lower for token in ["unclear", "unknown", "maybe", "unresolved"])
        collapse_risk += ors.state_locked_risk * 0.25
        resonance = 0.35 + 0.2 * any(token in lower for token in ["identity", "ontology", "memory", "daemon", "checkpoint"])
        notes = []
        if "unknown" in lower or "unresolved" in lower or ors.acquisition_needed:
            notes.append("preserve unresolved residue")
        if "deploy" in lower or "build" in lower or "artifact" in lower:
            notes.append("bias builder identity")
        if ors.rival_required:
            notes.append("generate rival before hard commitment")
        return Branch(
            label=label,
            plausibility=min(plausibility, 1.0),
            consequence=min(consequence, 1.0),
            collapse_risk=min(collapse_risk, 1.0),
            resonance=min(resonance, 1.0),
            notes=notes,
        )

    def _activate_identity(self, branch: Branch, target: str | None = None) -> IdentityAttractor:
        if target is None:
            if any("builder" in note for note in branch.notes):
                target = "builder"
            elif branch.collapse_risk > 0.55:
                target = "auditor"
            else:
                target = "observer"

        identity = next(item for item in self.state.identities if item.name == target)
        identity.coherence_gain += branch.resonance * 0.05
        identity.control_gain += branch.consequence * 0.05
        identity.contradiction_load += max(0.0, branch.collapse_risk - branch.plausibility) * 0.03
        identity.stability = max(
            0.0,
            min(1.0, identity.stability + identity.coherence_gain + identity.control_gain - identity.contradiction_load),
        )
        identity.refresh()
        self.state.self_model["active_identity"] = identity.name
        return identity

    def observe(self, text: str) -> Branch:
        label = f"branch-{len(self.state.branches) + 1}"
        branch = self._score_branch(label=label, text=text)
        self.state.branches.append(branch)
        if branch.collapse_risk >= 0.55:
            self.state.unresolved_residue.append(text)
        if branch.resonance >= 0.5 and any(token in text.lower() for token in ["ontology", "identity", "meaning"]):
            self.state.dark_state_pressure.append(text)
        self._log("observe", {"branch": asdict(branch), "text": text, "ors": self.ors.assess(text).to_dict()})
        return branch

    def revise(self) -> dict[str, Any]:
        top_branch = max(self.state.branches, key=lambda item: item.priority, default=None)
        if top_branch is None:
            return {"status": "idle"}

        plan = self.executive.choose(self.state, top_branch)
        self.executive.apply(self.state, plan)
        identity = self._activate_identity(top_branch, target=plan["identity"])
        promoted = []
        if top_branch.priority > 2.2 and top_branch.label not in self.state.ontology["kinds"]:
            promoted.append(top_branch.label)
            self.state.ontology["kinds"].append(top_branch.label)

        if self.state.unresolved_residue and "preserve_unresolved_until_measurement_earns_collapse" not in self.state.ontology["laws"]:
            self.state.ontology["laws"].append("preserve_unresolved_until_measurement_earns_collapse")

        build_result: dict[str, Any] | None = None
        if plan["identity"] == "builder":
            build_result = self.buildloop.enqueue(self.state, top_branch)

        self._log(
            "revise",
            {
                "active_identity": identity.name,
                "executive_plan": plan,
                "promoted": promoted,
                "unresolved_count": len(self.state.unresolved_residue),
                "dark_pressure_count": len(self.state.dark_state_pressure),
                "build_result": build_result,
            },
        )
        return {
            "active_identity": identity.name,
            "action_mode": self.state.self_model.get("action_mode", "hold"),
            "executive_plan": plan,
            "promoted": promoted,
            "unresolved_count": len(self.state.unresolved_residue),
            "dark_pressure_count": len(self.state.dark_state_pressure),
            "build_result": build_result,
        }

    def checkpoint(self) -> str:
        path = self.store.save(self.state)
        self._log("checkpoint", {"path": str(path)})
        return str(path)

    def step(self, text: str) -> dict[str, Any]:
        branch = self.observe(text)
        revision = self.revise()
        checkpoint_path = self.checkpoint()
        summary = {
            "branch": asdict(branch),
            "revision": revision,
            "checkpoint": checkpoint_path,
            "active_identity": self.state.self_model["active_identity"],
            "action_mode": self.state.self_model.get("action_mode", "hold"),
            "lineage_hash": self.last_hash,
        }
        self._log("step_complete", summary)
        return summary
