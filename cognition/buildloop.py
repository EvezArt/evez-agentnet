from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .models import Branch, CognitionState, utc_now


class BuildLoop:
    def __init__(self, root: str | Path = ".state") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue_path = self.root / "build_queue.jsonl"
        self.artifacts_dir = self.root / "draft_artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, state: CognitionState, branch: Branch) -> dict[str, Any]:
        item = {
            "at": utc_now(),
            "identity": state.self_model.get("active_identity", "observer"),
            "label": branch.label,
            "priority": branch.priority,
            "notes": branch.notes,
        }
        with self.queue_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item) + "\n")
        artifact = self.artifacts_dir / f"{branch.label}.md"
        # Context-brief: the artifact must carry the STATE THAT SPAWNED IT —
        # scan signals, predictions, the residue, the branch's own scores —
        # so a shipped brief is substance, not a stub asking someone else to
        # think. (The old form shipped "Convert this file into a task" every
        # 30 minutes: noise wearing work's uniform.)
        recent = [b for b in state.branches[-8:]]
        residue = state.unresolved_residue[-5:]
        self_model = state.self_model
        artifact.write_text(
            "\n".join([
                f"# Artifact for {branch.label}",
                "",
                f"Generated at: {item['at']}",
                f"Active identity: {item['identity']}",
                f"Priority: {branch.priority:.2f}",
                f"Action mode: {self_model.get('action_mode', 'hold')}",
                f"Predictor entropy (normalized): {self_model.get('predictor_entropy')}",
                f"Unresolved residue ({len(state.unresolved_residue)}): {residue if residue else 'none'}",
                "",
                "## The branch that commanded this build",
                f"- plausibility {branch.plausibility:.2f} / consequence {branch.consequence:.2f} / "
                f"collapse_risk {branch.collapse_risk:.2f} / resonance {branch.resonance:.2f}",
                *[f"- {note}" for note in branch.notes],
                "",
                "## Recent observations the builder can use",
                *[
                    f"- {b.label}: priority {b.priority:.2f}, "
                    f"notes: {'; '.join(b.notes) if b.notes else 'none'}"
                    for b in recent
                ],
                "",
                "## Doctrine reminder",
                "Chain or it didn't happen. The builder's brief is evidence-grade: "
                "every claim herein traces to daemon state at generation time.",
            ]),
            encoding="utf-8",
        )
        return {"queue_item": item, "artifact": str(artifact)}
