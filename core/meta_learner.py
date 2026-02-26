"""
META-LEARNER
Observes generator outputs over time and improves the system itself.

What this does:
  - Generator A keeps surfacing candidates that score 80 but never materialize
    -> MetaLearner detects the miscalibration, adjusts the scoring function
  - Primitive combo [ethena + kamino + marginfi] keeps appearing in top candidates
    -> MetaLearner elevates it to a first-class Architecture template
  - G4 DAO scanner produces 40 candidates/week but only 1 is actionable
    -> MetaLearner reduces G4 run frequency, increases score floor
  - A new pattern appears in episodic memory 3+ times
    -> MetaLearner drafts a new mini-generator targeted at that specific surface

The MetaLearner doesn't just run the system. It rewrites the playbook.
"""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Any
from core.agent_memory import AgentMemory

LEARNED_WEIGHTS_PATH = Path("memory/learned_weights.json")
GENERATOR_PROFILES_PATH = Path("memory/generator_profiles.json")
DISCOVERED_PATTERNS_PATH = Path("memory/discovered_patterns.jsonl")


class MetaLearner:
    def __init__(self, memory: AgentMemory):
        self.memory = memory
        self.learned_weights = self._load_json(LEARNED_WEIGHTS_PATH, {})
        self.generator_profiles = self._load_json(GENERATOR_PROFILES_PATH, {})

    def run_full_learning_cycle(self) -> dict:
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "weight_adjustments": [],
            "generator_reprioritizations": [],
            "new_patterns": [],
            "promoted_combinations": [],
            "proposed_generators": [],
        }
        report["weight_adjustments"] = self._recalibrate_scoring_weights()
        report["generator_reprioritizations"] = self._reprioritize_generators()
        report["new_patterns"] = self._extract_new_patterns()
        report["promoted_combinations"] = self._promote_combinations()
        report["proposed_generators"] = self._propose_new_generators()
        report_path = Path("memory") / f"learning_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return report

    def _recalibrate_scoring_weights(self) -> list:
        adjustments = []
        for gen_name in self.memory.meta.get_generator_performance():
            cal = self.memory.meta.get_score_calibration(gen_name)
            if not cal["calibrated"]:
                continue
            current_floor = self.learned_weights.get(gen_name, {}).get("score_floor", 60)
            recommended_floor = cal["recommended_floor"]
            if abs(recommended_floor - current_floor) >= 5:
                direction = "raised" if recommended_floor > current_floor else "lowered"
                self.learned_weights.setdefault(gen_name, {})["score_floor"] = recommended_floor
                adjustments.append({
                    "generator": gen_name, "old_floor": current_floor,
                    "new_floor": recommended_floor, "direction": direction,
                    "sample_size": cal["sample_size"],
                })
        self._save_json(LEARNED_WEIGHTS_PATH, self.learned_weights)
        return adjustments

    def _reprioritize_generators(self) -> list:
        reprioritizations = []
        perf = self.memory.meta.get_generator_performance()
        for gen_name, stats in perf.items():
            rate = stats.get("actionable_rate", 0)
            current_priority = self.generator_profiles.get(gen_name, {}).get("priority", 5)
            if rate >= 0.25 and current_priority < 8:
                new_priority = min(current_priority + 1, 10)
                label = "boosted"
            elif rate < 0.05 and current_priority > 2:
                new_priority = max(current_priority - 1, 1)
                label = "throttled"
            else:
                continue
            self.generator_profiles.setdefault(gen_name, {})["priority"] = new_priority
            reprioritizations.append({
                "generator": gen_name, "actionable_rate": round(rate, 3),
                "old_priority": current_priority, "new_priority": new_priority,
                "action": label,
            })
        self._save_json(GENERATOR_PROFILES_PATH, self.generator_profiles)
        return reprioritizations

    def _extract_new_patterns(self) -> list:
        recent = self.memory.episodic.get_recent(hours=720)
        new_patterns = []
        feature_counter = Counter()
        for episode in recent:
            data = episode.get("data", {})
            for field in ["category", "chain", "mev_surface", "type"]:
                if data.get(field):
                    feature_counter[f"{field}:{data[field]}"] += 1
        known_patterns = self._load_discovered_pattern_ids()
        for feature, count in feature_counter.most_common(20):
            if count >= 3 and feature not in known_patterns:
                pattern = {
                    "id": feature.replace(":", "_").replace(" ", "_"),
                    "feature": feature, "occurrences": count,
                    "discovered": datetime.utcnow().isoformat(), "status": "candidate",
                }
                new_patterns.append(pattern)
                with open(DISCOVERED_PATTERNS_PATH, "a") as f:
                    f.write(json.dumps(pattern) + "\n")
        return new_patterns

    def _promote_combinations(self) -> list:
        promotions = []
        best = self.memory.meta.get_best_primitive_combos(top_n=10)
        for combo in best:
            if combo["attempts"] >= 3 and combo["avg_yield"] >= 20:
                template_key = f"architecture_template:{combo['key']}"
                existing, conf = self.memory.semantic.get_with_confidence(template_key)
                if existing is None:
                    self.memory.semantic.set(
                        template_key,
                        {"primitives": combo["primitives"], "avg_yield": combo["avg_yield"],
                         "attempts": combo["attempts"], "promoted_at": datetime.utcnow().isoformat()},
                        confidence=min(combo["attempts"] / 10, 1.0),
                        source="MetaLearner._promote_combinations"
                    )
                    promotions.append(combo)
        return promotions

    def _propose_new_generators(self) -> list:
        proposals = []
        patterns = self._load_discovered_patterns()
        high_freq = [p for p in patterns if p["occurrences"] >= 5 and p["status"] == "candidate"]
        for pattern in high_freq[:3]:
            proposal = {
                "type": "pattern_targeted",
                "trigger": pattern["feature"],
                "occurrences": pattern["occurrences"],
                "proposed_id": f"g_auto_{pattern['id']}",
                "description": (
                    f"Auto-generated generator targeting '{pattern['feature']}'. "
                    f"Observed {pattern['occurrences']}x in last 30 days without dedicated coverage."
                ),
                "status": "proposed",
                "proposed_at": datetime.utcnow().isoformat(),
            }
            proposals.append(proposal)
        recent = self.memory.episodic.get_recent(hours=720)
        missed = [
            ep for ep in recent
            if ep.get("data", {}).get("_score", 100) < 60 and ep.get("outcome") == "materialized"
        ]
        if len(missed) >= 3:
            proposals.append({
                "type": "recovery_generator",
                "missed_count": len(missed),
                "description": (
                    f"{len(missed)} low-scored candidates materialized in last 30 days. "
                    f"Scoring function systematically undervaluing a class of opportunities."
                ),
                "status": "proposed",
                "proposed_at": datetime.utcnow().isoformat(),
            })
        for p in proposals:
            self.memory.semantic.set(
                f"generator_proposal:{p.get('proposed_id', p['type'])}",
                p, confidence=0.6, source="MetaLearner._propose_new_generators"
            )
        return proposals

    def _load_discovered_patterns(self) -> list:
        if not DISCOVERED_PATTERNS_PATH.exists():
            return []
        with open(DISCOVERED_PATTERNS_PATH) as f:
            return [json.loads(l) for l in f if l.strip()]

    def _load_discovered_pattern_ids(self) -> set:
        return {p["feature"] for p in self._load_discovered_patterns()}

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with open(path) as f:
            return json.load(f)

    def _save_json(self, path: Path, data: Any) -> None:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)


if __name__ == "__main__":
    from core.agent_memory import AgentMemory
    mem = AgentMemory()
    learner = MetaLearner(mem)
    report = learner.run_full_learning_cycle()
    print(json.dumps(report, indent=2, default=str))
