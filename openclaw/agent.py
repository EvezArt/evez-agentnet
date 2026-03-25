# openclaw/agent.py
# OpenClawAgent — OODA-integrated agent for the evez-agentnet swarm
# Author: Steven Crawford-Maggard (EVEZ666)

"""
OpenClawAgent wraps OpenClawEngine into the evez-agentnet OODA loop.
Can be deployed as a standalone agent or plugged into orchestrator.py.

OODA roles:
  Observe  — reads worldsim state + scanner signals
  Orient   — LordBridge entropy injection, tier unlock assessment
  Decide   — schedule run, set max_iterations based on signal strength
  Act      — runs OpenClawEngine, writes secret_levels_state.json, appends to ship_log
"""

import json
import os
from datetime import datetime
from pathlib import Path

from openclaw.engine import OpenClawEngine
from openclaw.lord_bridge import LordBridge

SHIP_LOG = Path("shipper/ship_log.jsonl")
SCAN_RESULTS = Path("scanner/scan_results.jsonl")


class OpenClawAgent:
    """evez-agentnet agent: wraps OpenClawEngine in OODA loop."""

    def __init__(self, lord_mode="auto", max_iterations=500, verbose=True):
        self.lord_bridge = LordBridge(mode=lord_mode)
        self.engine = OpenClawEngine(
            lord_bridge=self.lord_bridge,
            max_iterations=max_iterations,
            verbose=verbose,
        )
        self.verbose = verbose

    # ─── OBSERVE ─────────────────────────────────────────────────────────────
    def observe(self) -> dict:
        """Read latest scan signals relevant to worldsim."""
        signals = {
            "scan_count": 0,
            "trending_topics": [],
            "market_confidence": 0.5,
        }
        if SCAN_RESULTS.exists():
            try:
                lines = SCAN_RESULTS.read_text().strip().splitlines()
                signals["scan_count"] = len(lines)
                if lines:
                    last = json.loads(lines[-1])
                    signals["market_confidence"] = last.get("confidence", 0.5)
                    signals["trending_topics"] = last.get("topics", [])
            except Exception as e:
                if self.verbose:
                    print(f"[OpenClawAgent] Observe error: {e}")
        return signals

    # ─── ORIENT ──────────────────────────────────────────────────────────────
    def orient(self, signals: dict) -> dict:
        """Assess entropy and decide urgency."""
        confidence = signals.get("market_confidence", 0.5)
        current_entropy = self.lord_bridge.get_entropy(
            self.engine.state.get("iteration", 0)
        )
        # High market confidence = inject entropy pulse (accelerate convergence)
        if confidence > 0.75:
            self.lord_bridge.inject_lord_event("entropy_pulse", {"delta": -0.03})
        orientation = {
            "entropy": current_entropy,
            "tier_status": {
                "TIER_1": self.engine.state.get("TIER_1_unlocked", False),
                "TIER_2": self.engine.state.get("TIER_2_unlocked", False),
                "TIER_3_SECRET": self.engine.state.get("TIER_3_SECRET_unlocked", False),
            },
            "living_entities": self.engine.state.get("living_entities", 0),
            "market_confidence": confidence,
        }
        return orientation

    # ─── DECIDE ──────────────────────────────────────────────────────────────
    def decide(self, orientation: dict) -> int:
        """Compute number of iterations to run this cycle."""
        # If all secret levels unlocked — minimal maintenance run
        if orientation["tier_status"]["TIER_3_SECRET"]:
            return 10
        # If entropy low — we're close, run longer
        if orientation["entropy"] < 0.30:
            return 200
        return 100

    # ─── ACT ─────────────────────────────────────────────────────────────────
    def act(self, iterations: int) -> dict:
        """Run the engine for the given number of iterations."""
        self.engine.max_iterations = iterations
        final_state = self.engine.run()
        self._log_ship(final_state)
        return final_state

    def _log_ship(self, state: dict):
        """Append run result to ship_log.jsonl."""
        SHIP_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "agent": "OpenClawAgent",
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": state.get("iteration"),
            "unlocked_levels": state.get("unlocked_levels", []),
            "living_entities": state.get("living_entities", 0),
            "reputation": state.get("reputation"),
            "lord_entropy": state.get("lord_entropy"),
            "TIER_3_SECRET_unlocked": state.get("TIER_3_SECRET_unlocked", False),
        }
        with open(SHIP_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ─── FULL OODA CYCLE ─────────────────────────────────────────────────────
    def run_ooda_cycle(self) -> dict:
        """Execute a full Observe-Orient-Decide-Act cycle."""
        if self.verbose:
            print("[OpenClawAgent] OODA cycle starting...")
        signals = self.observe()
        orientation = self.orient(signals)
        iterations = self.decide(orientation)
        if self.verbose:
            print(f"[OpenClawAgent] entropy={orientation['entropy']:.4f} "
                  f"iterations={iterations} "
                  f"entities={orientation['living_entities']}")
        return self.act(iterations)
