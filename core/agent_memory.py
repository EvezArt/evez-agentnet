"""
AGENT MEMORY & STATE
The cognitive substrate. Persists everything the agent has observed, scored,
acted on, and learned from. Enables genuine learning loops.

Architecture:
  - EpisodicMemory: what happened (observations, actions, outcomes)
  - SemanticMemory: what is known (compressed facts, patterns, models)
  - WorkingMemory: what is currently active (attention, goals, context)
  - MetaMemory: what works (generator performance, scoring calibration, combo tracking)
"""
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)


class EpisodicMemory:
    """Time-stamped log of agent observations and actions."""
    def __init__(self):
        self.path = MEMORY_DIR / "episodic.jsonl"

    def record(self, event_type: str, data: dict, outcome: str = None) -> str:
        episode_id = hashlib.md5(f"{event_type}{time.time()}".encode()).hexdigest()[:10]
        episode = {
            "id": episode_id,
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "outcome": outcome,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(episode) + "\n")
        return episode_id

    def update_outcome(self, episode_id: str, outcome: str, reward: float) -> None:
        episodes = self._load_all()
        for ep in episodes:
            if ep["id"] == episode_id:
                ep["outcome"] = outcome
                ep["reward"] = reward
                break
        self._save_all(episodes)

    def get_recent(self, hours: int = 168, event_type: str = None) -> list:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = []
        for ep in self._load_all():
            ts = datetime.fromisoformat(ep["timestamp"])
            if ts < cutoff:
                continue
            if event_type and ep["type"] != event_type:
                continue
            result.append(ep)
        return result

    def _load_all(self) -> list:
        if not self.path.exists():
            return []
        with open(self.path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def _save_all(self, episodes: list) -> None:
        with open(self.path, "w") as f:
            for ep in episodes:
                f.write(json.dumps(ep) + "\n")


class SemanticMemory:
    """Compressed world model. Extracted facts and patterns."""
    def __init__(self):
        self.path = MEMORY_DIR / "semantic.json"
        self._facts = self._load()

    def set(self, key: str, value: Any, confidence: float = 1.0, source: str = "") -> None:
        self._facts[key] = {
            "value": value,
            "confidence": confidence,
            "source": source,
            "updated": datetime.utcnow().isoformat(),
        }
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._facts.get(key)
        return entry["value"] if entry else default

    def get_with_confidence(self, key: str):
        entry = self._facts.get(key)
        if not entry:
            return None, 0.0
        return entry["value"], entry["confidence"]

    def search(self, pattern: str) -> dict:
        return {k: v for k, v in self._facts.items() if pattern.lower() in k.lower()}

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._facts, f, indent=2, default=str)


class WorkingMemory:
    """Active context window for the current reasoning cycle."""
    def __init__(self):
        self.path = MEMORY_DIR / "working.json"
        self.state = self._load()

    def set_goal(self, goal: str, priority: int = 5) -> None:
        self.state.setdefault("goals", [])
        self.state["goals"].append({"goal": goal, "priority": priority, "created": datetime.utcnow().isoformat()})
        self._save()

    def get_goals(self, min_priority: int = 0) -> list:
        return sorted(
            [g for g in self.state.get("goals", []) if g["priority"] >= min_priority],
            key=lambda x: -x["priority"]
        )

    def clear_goals(self) -> None:
        self.state["goals"] = []
        self._save()

    def set_focus(self, focus: str) -> None:
        self.state["current_focus"] = focus
        self.state["focus_set"] = datetime.utcnow().isoformat()
        self._save()

    def get_focus(self) -> str:
        return self.state.get("current_focus", "idle")

    def push_signal(self, signal: dict) -> None:
        self.state.setdefault("live_signals", [])
        self.state["live_signals"].append({**signal, "pushed": datetime.utcnow().isoformat()})
        self._save()

    def flush_signals(self) -> list:
        signals = self.state.pop("live_signals", [])
        self._save()
        return signals

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2, default=str)


class MetaMemory:
    """The agent's model of its own performance."""
    def __init__(self):
        self.path = MEMORY_DIR / "meta.json"
        self._meta = self._load()

    def record_generator_run(self, generator: str, candidates: int, high_score: int, runtime_s: float) -> None:
        g = self._meta.setdefault("generators", {}).setdefault(generator, {
            "runs": 0, "total_candidates": 0, "total_high_score": 0,
            "total_runtime_s": 0, "actionable_rate": 0.0,
        })
        g["runs"] += 1
        g["total_candidates"] += candidates
        g["total_high_score"] += high_score
        g["total_runtime_s"] += runtime_s
        g["actionable_rate"] = g["total_high_score"] / max(g["total_candidates"], 1)
        g["last_run"] = datetime.utcnow().isoformat()
        self._save()

    def get_generator_performance(self) -> dict:
        return self._meta.get("generators", {})

    def get_best_generators(self, top_n: int = 3) -> list:
        perf = self.get_generator_performance()
        return sorted(perf.keys(), key=lambda g: perf[g].get("actionable_rate", 0), reverse=True)[:top_n]

    def record_scoring_outcome(self, generator: str, score: float, materialized: bool) -> None:
        outcomes = self._meta.setdefault("scoring_outcomes", [])
        outcomes.append({
            "generator": generator, "score": score,
            "materialized": materialized, "timestamp": datetime.utcnow().isoformat(),
        })
        self._meta["scoring_outcomes"] = outcomes[-500:]
        self._save()

    def get_score_calibration(self, generator: str) -> dict:
        outcomes = [o for o in self._meta.get("scoring_outcomes", []) if o["generator"] == generator]
        if len(outcomes) < 10:
            return {"calibrated": False, "recommended_floor": 60}
        buckets = defaultdict(lambda: {"total": 0, "materialized": 0})
        for o in outcomes:
            bucket = (int(o["score"]) // 10) * 10
            buckets[bucket]["total"] += 1
            buckets[bucket]["materialized"] += int(o["materialized"])
        calibrated_floor = 60
        for threshold in sorted(buckets.keys()):
            b = buckets[threshold]
            if b["total"] > 0 and b["materialized"] / b["total"] >= 0.5:
                calibrated_floor = threshold
                break
        return {"calibrated": True, "recommended_floor": calibrated_floor,
                "buckets": dict(buckets), "sample_size": len(outcomes)}

    def record_architecture_outcome(self, primitive_ids: list, net_yield_realized: float) -> None:
        arch_key = "_".join(sorted(primitive_ids))
        arches = self._meta.setdefault("architecture_outcomes", {})
        entry = arches.setdefault(arch_key, {"attempts": 0, "total_yield": 0.0, "primitives": primitive_ids})
        entry["attempts"] += 1
        entry["total_yield"] += net_yield_realized
        entry["avg_yield"] = entry["total_yield"] / entry["attempts"]
        entry["last_updated"] = datetime.utcnow().isoformat()
        self._save()

    def get_best_primitive_combos(self, top_n: int = 5) -> list:
        arches = self._meta.get("architecture_outcomes", {})
        return sorted(
            [{"key": k, **v} for k, v in arches.items() if v["attempts"] >= 2],
            key=lambda x: x.get("avg_yield", 0), reverse=True
        )[:top_n]

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            return json.load(f)

    def _save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._meta, f, indent=2, default=str)


class AgentMemory:
    """Single access point for all memory systems."""
    def __init__(self):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.working = WorkingMemory()
        self.meta = MetaMemory()

    def snapshot(self) -> dict:
        return {
            "focus": self.working.get_focus(),
            "active_goals": len(self.working.get_goals()),
            "live_signals": len(self.working.state.get("live_signals", [])),
            "known_facts": len(self.semantic._facts),
            "best_generators": self.meta.get_best_generators(),
            "best_combos": self.meta.get_best_primitive_combos(top_n=3),
        }
