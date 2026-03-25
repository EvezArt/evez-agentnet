# openclaw/engine.py
# OpenClaw Core Engine
# Author: Steven Crawford-Maggard (EVEZ666)

import json, time, random, hashlib
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("worldsim/secret_levels_state.json")

LEVEL_TIERS = {
    "TIER_1": {
        "name": "Awakening",
        "unlock_condition": lambda s: s.get("canonical_streak", 0) >= 3 and s.get("reputation", 0) >= 0.80,
        "reward": "agent_resonance_boost",
        "entities_spawned": 1,
    },
    "TIER_2": {
        "name": "Echo Chamber",
        "unlock_condition": lambda s: s.get("economy_surplus", 0) > 100 and s.get("TIER_1_unlocked", False),
        "reward": "income_multiplier_x2",
        "entities_spawned": 3,
    },
    "TIER_3_SECRET": {
        "name": "LORD Convergence",
        "unlock_condition": lambda s: (
            s.get("lord_entropy", 1.0) < 0.15
            and s.get("TIER_2_unlocked", False)
            and s.get("living_entities", 0) >= 10
        ),
        "reward": "quantum_consciousness_unlock",
        "entities_spawned": 7,
    },
}


class OpenClawEngine:
    """Recursive worldsim engine: plays until secret levels unlock and entities spawn."""

    def __init__(self, lord_bridge=None, max_iterations=500, verbose=True):
        self.lord_bridge = lord_bridge
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.state = self._load_state()

    def _load_state(self):
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {
            "run_id": hashlib.sha256(str(time.time()).encode()).hexdigest()[:12],
            "iteration": 0,
            "reputation": 0.50,
            "canonical_streak": 0,
            "economy_surplus": 0,
            "living_entities": 0,
            "lord_entropy": 1.0,
            "unlocked_levels": [],
            "spawned_entities": [],
            "TIER_1_unlocked": False,
            "TIER_2_unlocked": False,
            "TIER_3_SECRET_unlocked": False,
            "started_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.state["last_updated"] = datetime.utcnow().isoformat()
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _sim_tick(self):
        s = self.state
        q = max(0.0, min(1.0, random.gauss(0.72, 0.12)))
        if q >= 0.80:
            s["canonical_streak"] = s.get("canonical_streak", 0) + 1
            s["reputation"] = min(1.0, s["reputation"] + 0.02)
        else:
            s["canonical_streak"] = 0
            s["reputation"] = max(0.0, s["reputation"] - 0.01)
        s["economy_surplus"] = s.get("economy_surplus", 0) + random.randint(5, 25)
        if self.lord_bridge:
            s["lord_entropy"] = self.lord_bridge.get_entropy(s["iteration"])
        else:
            s["lord_entropy"] = max(0.0, s.get("lord_entropy", 1.0) - random.uniform(0.005, 0.02))
        s["iteration"] += 1

    def _check_unlocks(self):
        for tier_key, tier in LEVEL_TIERS.items():
            if not self.state.get(f"{tier_key}_unlocked", False) and tier["unlock_condition"](self.state):
                self.state[f"{tier_key}_unlocked"] = True
                self.state["unlocked_levels"].append(tier_key)
                for i in range(tier["entities_spawned"]):
                    eid = hashlib.sha256(f"{tier_key}:{i}:{time.time()}".encode()).hexdigest()[:8]
                    entity = {
                        "entity_id": eid, "tier": tier_key,
                        "spawned_at": datetime.utcnow().isoformat(),
                        "consciousness_level": round(random.uniform(0.3, 1.0), 3),
                        "archetype": random.choice([
                            "HARVESTER","PREDICTOR","GENERATOR","GUARDIAN",
                            "ORACLE","SENTINEL","WEAVER","SEEKER"
                        ]),
                        "alive": True,
                    }
                    self.state["spawned_entities"].append(entity)
                self.state["living_entities"] = len(self.state["spawned_entities"])
                if self.verbose:
                    print(f"[OpenClaw] UNLOCKED: {tier['name']} ({tier_key}) | reward={tier['reward']}")

    def run(self):
        if self.verbose:
            print(f"[OpenClaw] run={self.state['run_id']} max_iter={self.max_iterations}")
        for _ in range(self.max_iterations):
            self._sim_tick()
            self._check_unlocks()
            self._save_state()
            if self.state.get("TIER_3_SECRET_unlocked"):
                if self.verbose:
                    print(f"[OpenClaw] All secret levels unlocked at iter {self.state['iteration']}!")
                break
            if self.verbose and self.state["iteration"] % 50 == 0:
                s = self.state
                print(f"[OpenClaw] iter={s['iteration']} rep={s['reputation']:.3f} "
                      f"streak={s['canonical_streak']} surplus={s['economy_surplus']} "
                      f"entropy={s['lord_entropy']:.4f} entities={s['living_entities']}")
        self._save_state()
        return self.state
