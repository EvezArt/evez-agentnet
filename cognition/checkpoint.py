from __future__ import annotations

from pathlib import Path
import json

from .models import CognitionState, utc_now


class CheckpointStore:
    def __init__(self, root: str | Path = ".state") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "latest.json"

    def save(self, state: CognitionState) -> Path:
        state.updated_at = utc_now()
        checkpoint_path = self.root / f"checkpoint-{state.checkpoint_id}.json"
        checkpoint_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        self.index_path.write_text(json.dumps({"latest": checkpoint_path.name}, indent=2), encoding="utf-8")
        return checkpoint_path

    def load_latest(self) -> CognitionState | None:
        if not self.index_path.exists():
            return None
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        latest = payload.get("latest")
        if not latest:
            return None
        checkpoint_path = self.root / latest
        if not checkpoint_path.exists():
            return None
        state_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        return CognitionState.from_dict(state_payload)
