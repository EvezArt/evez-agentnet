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
        artifact.write_text(
            "\n".join([
                f"# Artifact for {branch.label}",
                "",
                f"Generated at: {item['at']}",
                f"Active identity: {item['identity']}",
                f"Priority: {item['priority']:.2f}",
                "",
                "## Notes",
                *[f"- {note}" for note in branch.notes],
                "",
                "## Next step",
                "Convert this file into a concrete repo task, code stub, or document.",
            ]),
            encoding="utf-8",
        )
        return {"queue_item": item, "artifact": str(artifact)}
