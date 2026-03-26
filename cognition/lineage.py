from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json


@dataclass
class LineageEvent:
    kind: str
    payload: dict
    parent_hash: str

    def digest(self) -> str:
        raw = json.dumps({"kind": self.kind, "payload": self.payload, "parent_hash": self.parent_hash}, sort_keys=True).encode("utf-8")
        return sha256(raw).hexdigest()


class LineageStore:
    def __init__(self, root: str | Path = ".state") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "lineage.jsonl"

    def append(self, event: LineageEvent) -> str:
        digest = event.digest()
        row = {"kind": event.kind, "payload": event.payload, "parent_hash": event.parent_hash, "hash": digest}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return digest
