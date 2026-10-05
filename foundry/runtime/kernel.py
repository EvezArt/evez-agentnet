from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any

LEVELS = {
    "OBSERVE": 0, "DERIVE": 1, "TEST": 2, "SIMULATE": 3,
    "BRANCH": 4, "ISSUE": 5, "PATCH": 6, "NONPROD": 7,
    "DEPLOY": 8, "EXTERNAL": 9,
}

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

class EvidenceSpine:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = line
        if not last:
            return "0" * 64
        return json.loads(last)["hash"]

    def append(self, event_type: str, payload: dict[str, Any], status: str = "OBSERVED") -> str:
        event = {
            "schema": "evez.generated-os.event.v1",
            "event_type": event_type,
            "status": status,
            "observed_at": time.time(),
            "payload": payload,
            "parent_hash": self.last_hash(),
        }
        event["hash"] = digest(event)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(canonical(event) + "\n")
        return event["hash"]

    def verify(self) -> bool:
        parent = "0" * 64
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            stored = event.pop("hash")
            if event.get("parent_hash") != parent or digest(event) != stored:
                return False
            parent = stored
        return True

class Policy:
    def __init__(self, maximum_autonomy: int = 5):
        if not 0 <= maximum_autonomy <= 9:
            raise ValueError("maximum_autonomy must be between 0 and 9")
        self.maximum_autonomy = maximum_autonomy

    def allowed(self, action: str) -> bool:
        if action not in LEVELS:
            raise ValueError(f"unknown action: {action}")
        return LEVELS[action] <= self.maximum_autonomy

class Kernel:
    def __init__(self, manifest: dict[str, Any], root: Path):
        self.manifest = manifest
        self.root = root
        self.spine = EvidenceSpine(root / "evidence" / "spine.jsonl")
        self.policy = Policy(int(manifest["authority"]["maximum_autonomy"]))
        self.state = "CREATED"
        self.agents = {name: {"name": name, "status": "DECLARED"} for name in manifest.get("agents", [])}

    def boot(self) -> dict[str, Any]:
        if self.state != "CREATED":
            raise RuntimeError(f"cannot boot from {self.state}")
        self.state = "BOOTING"
        self.spine.append("BOOT_START", {
            "os_id": self.manifest["os_id"],
            "generation": self.manifest["generation"],
        })
        self.state = "READY"
        event_hash = self.spine.append("BOOT_READY", {
            "agents": sorted(self.agents),
            "authority": self.policy.maximum_autonomy,
        })
        return {"state": self.state, "event_hash": event_hash, "spine_valid": self.spine.verify()}

    def request(self, agent: str, action: str, **payload: Any) -> dict[str, Any]:
        if self.state != "READY":
            raise RuntimeError("kernel is not ready")
        if agent not in self.agents:
            raise KeyError(f"unknown agent: {agent}")
        allowed = self.policy.allowed(action)
        status = "ALLOWED" if allowed else "BLOCKED"
        event_hash = self.spine.append("ACTION_REQUEST", {
            "agent": agent,
            "action": action,
            "allowed": allowed,
            "payload": payload,
        }, status=status)
        return {"allowed": allowed, "status": status, "event_hash": event_hash}

    def halt(self) -> dict[str, Any]:
        if self.state == "HALTED":
            return {"state": self.state}
        event_hash = self.spine.append("HALT", {"previous_state": self.state})
        self.state = "HALTED"
        return {"state": self.state, "event_hash": event_hash}
