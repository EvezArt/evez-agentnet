from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any

ALLOWED_KINDS = {"USER_STATEMENT", "OBSERVATION", "INFERENCE", "PROPOSAL", "UNKNOWN"}

class MemoryStore:
    """Append-only, provenance-aware local memory.

    A memory item is never silently upgraded from inference to fact.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _digest(self, value: dict[str, Any]) -> str:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def add(self, kind: str, content: str, source: str = "LOCAL") -> dict[str, Any]:
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"unknown memory kind: {kind}")
        item = {
            "schema": "evez.memory.v1",
            "kind": kind,
            "content": content,
            "source": source,
            "observed_at": time.time(),
        }
        item["id"] = "mem-" + self._digest(item)[:20]
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")
        return item

    def search(self, query: str, kinds: set[str] | None = None, limit: int = 20) -> list[dict[str, Any]]:
        terms = {term for term in query.lower().split() if term}
        results = []
        if not self.path.exists():
            return results
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if kinds and item["kind"] not in kinds:
                continue
            text = item["content"].lower()
            score = sum(1 for term in terms if term in text)
            if score:
                results.append((score, item))
        results.sort(key=lambda pair: (-pair[0], pair[1]["observed_at"]))
        return [item for _, item in results[:limit]]
