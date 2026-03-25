"""
MAES Connector Agent
====================
Registers MAES as a node in the evez-agentnet OODA orchestrator.
Pulls /agents and /events from MAES and injects results into the
orchestrator's observation bus so OODA loops can react to agent ecology.
"""

import os
import time
import json
import httpx
from typing import Any

MAES_URL = os.getenv("MAES_URL", "https://maes.railway.app")
POLL_INTERVAL = int(os.getenv("MAES_POLL_INTERVAL", "5"))


class MAESConnector:
    """Lightweight connector that bridges MAES ↔ OODA observation bus."""

    def __init__(self, observation_bus: list[dict]):
        self.bus = observation_bus
        self.last_event_pos = 0
        self.client = httpx.Client(timeout=8)

    def health(self) -> bool:
        try:
            r = self.client.get(f"{MAES_URL}/health")
            return r.status_code == 200
        except Exception:
            return False

    def fetch_agents(self) -> list[dict]:
        try:
            r = self.client.get(f"{MAES_URL}/agents")
            return r.json().get("agents", []) if r.status_code == 200 else []
        except Exception:
            return []

    def fetch_new_events(self) -> list[dict]:
        try:
            r = self.client.get(f"{MAES_URL}/events", params={"from": self.last_event_pos})
            events = r.json().get("events", []) if r.status_code == 200 else []
            if events:
                self.last_event_pos = events[-1].get("position", self.last_event_pos) + 1
            return events
        except Exception:
            return []

    def spawn_agent(self, agent_type: str = "npc") -> dict | None:
        try:
            r = self.client.post(f"{MAES_URL}/agents/spawn", json={"type": agent_type})
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def verify_agent(self, agent_id: str) -> dict | None:
        try:
            r = self.client.get(f"{MAES_URL}/agents/{agent_id}/verify")
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def tick(self):
        """One OODA observe cycle: pull MAES state → push to bus."""
        agents = self.fetch_agents()
        new_events = self.fetch_new_events()

        players = [a for a in agents if a.get("playerStatus", {}) and a["playerStatus"].get("isPlayer")]

        observation = {
            "source": "maes_connector",
            "ts": time.time(),
            "agent_count": len(agents),
            "player_count": len(players),
            "new_events": len(new_events),
            "agents": agents,
            "fire_events": [e for e in new_events if "fire" in e.get("eventType", "")],
        }

        self.bus.append(observation)

        # RSI Hypothesis 3 trigger: 5+ verified players → emit scale.trigger
        if len(players) >= 5:
            self.bus.append({
                "source": "maes_connector",
                "ts": time.time(),
                "event": "scale.trigger",
                "player_count": len(players),
                "message": "5+ verified players detected. NPC ecology scaling recommended."
            })

        return observation

    def run_forever(self):
        print(f"[MAES Connector] Starting. MAES_URL={MAES_URL} interval={POLL_INTERVAL}s")
        while True:
            if self.health():
                obs = self.tick()
                print(f"[MAES] agents={obs['agent_count']} players={obs['player_count']} new_events={obs['new_events']}")
            else:
                print("[MAES] OFFLINE — retrying...")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    bus: list[dict] = []
    MAESConnector(bus).run_forever()
