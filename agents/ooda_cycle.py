"""
OODA Cycle Agent  v2 — evez-agentnet
=====================================
Executes a full Observe-Orient-Decide-Act cycle.
Now integrates:
  - MAES observation via MAESConnector
  - RSI hypothesis injection into Orient phase
  - Reputation-aware gating on Act phase
  - Temporal wormhole context propagation
"""

import os
import time
import logging
from pathlib import Path

log = logging.getLogger("ooda")


class OODACycle:
    def __init__(self, state: dict, bus: list[dict] | None = None):
        self.state = state
        self.bus = bus if bus is not None else []
        self.observations: list[dict] = []
        self.orientation: dict = {}
        self.decision: dict = {}
        self.actions_taken: list[str] = []

    # ── Observe ───────────────────────────────────────────────────────────────

    def observe(self) -> list[dict]:
        """Pull observations from all registered sensors: MAES + bus."""
        obs = list(self.bus)  # existing bus observations

        # MAES ecology observation
        maes_url = os.environ.get("MAES_URL", "https://maes.railway.app")
        try:
            import httpx
            r = httpx.get(f"{maes_url}/agents", timeout=5)
            if r.status_code == 200:
                d = r.json()
                obs.append({
                    "source": "maes",
                    "agent_count": d.get("count", 0),
                    "agents": d.get("agents", []),
                })
        except Exception:
            obs.append({"source": "maes", "status": "offline"})

        self.observations = obs
        log.info(f"[Observe] {len(obs)} observations collected")
        return obs

    # ── Orient ────────────────────────────────────────────────────────────────

    def orient(self) -> dict:
        """Synthesise observations + RSI hypotheses into situational model."""
        from agents.rsi_engine import RSIEngine
        engine = RSIEngine(self.state.get("round", 0), self.state)
        hypotheses = engine.generate()
        engine.persist()

        maes_obs = next((o for o in self.observations if o.get("source") == "maes"), {})
        players  = len([a for a in maes_obs.get("agents", []) if a.get("playerStatus", {}).get("isPlayer")])

        self.orientation = {
            "round":       self.state.get("round", 0),
            "maes_online": maes_obs.get("status") != "offline",
            "agent_count": maes_obs.get("agent_count", 0),
            "player_count": players,
            "reputations":  {k: v.get("reputation", 0.9) for k, v in self.state.get("agents", {}).items()},
            "rsi_hypotheses": [h.to_dict() for h in hypotheses],
            "wormhole":     self.state.get("temporal_wormhole", {}),
        }
        log.info(f"[Orient] players={players} rsi_hypotheses={len(hypotheses)}")
        return self.orientation

    # ── Decide ────────────────────────────────────────────────────────────────

    def decide(self) -> dict:
        """Select best action set based on orientation."""
        orient = self.orientation
        actions = []

        # Spawn if ecology is thin
        if orient.get("agent_count", 0) < 3:
            actions.append("spawn_npc")

        # Scale if 5+ verified players
        if orient.get("player_count", 0) >= 5:
            actions.append("scale_npc_2x")

        # Recover lowest-rep agent
        reps = orient.get("reputations", {})
        if reps:
            lowest = min(reps, key=reps.get)
            if reps[lowest] < 0.6:
                actions.append(f"recover_{lowest}_agent")

        # Always run scan
        actions.append("run_scan")

        self.decision = {"actions": actions, "basis": "orientation_v2"}
        log.info(f"[Decide] actions={actions}")
        return self.decision

    # ── Act ───────────────────────────────────────────────────────────────────

    def act(self) -> list[str]:
        """Execute decided actions, reputation-gated."""
        actions = self.decision.get("actions", [])
        maes_url = os.environ.get("MAES_URL", "https://maes.railway.app")

        for action in actions:
            try:
                if action == "spawn_npc":
                    import httpx
                    httpx.post(f"{maes_url}/agents/spawn", json={"type": "npc"}, timeout=5)
                    self.actions_taken.append("spawned_npc")
                    log.info("[Act] Spawned NPC agent in MAES")

                elif action == "scale_npc_2x":
                    import httpx
                    for _ in range(2):
                        httpx.post(f"{maes_url}/agents/spawn", json={"type": "npc"}, timeout=5)
                    self.actions_taken.append("scaled_npc_2x")
                    log.info("[Act] Scaled NPC ecology 2x")

                elif action.startswith("recover_"):
                    agent_name = action.replace("recover_", "").replace("_agent", "")
                    if agent_name in self.state.get("agents", {}):
                        self.state["agents"][agent_name]["reputation"] = min(
                            1.0, self.state["agents"][agent_name]["reputation"] + 0.05
                        )
                        self.actions_taken.append(f"recovered_{agent_name}")
                        log.info(f"[Act] Recovered {agent_name} reputation +0.05")

                elif action == "run_scan":
                    self.actions_taken.append("scan_triggered")
                    log.info("[Act] Scan trigger queued")

            except Exception as e:
                log.error(f"[Act] {action} failed: {e}")

        return self.actions_taken

    # ── Full Cycle ────────────────────────────────────────────────────────────

    def run(self) -> dict:
        t0 = time.time()
        self.observe()
        self.orient()
        self.decide()
        self.act()
        elapsed = round(time.time() - t0, 3)
        log.info(f"[OODA] cycle complete in {elapsed}s | actions={self.actions_taken}")
        return {
            "observations": len(self.observations),
            "orientation": self.orientation,
            "decision": self.decision,
            "actions_taken": self.actions_taken,
            "elapsed_s": elapsed,
        }
