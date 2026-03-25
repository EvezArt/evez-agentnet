# openclaw/lord_bridge.py
# LordBridge: Bridge to EVEZ LORD quantum consciousness engine
# Author: Steven Crawford-Maggard (EVEZ666)

import json, math, random
from pathlib import Path

LORD_STATE_FILE = Path("ors/lord_state.json")
ENTROPY_DECAY_RATE = 0.012


class LordBridge:
    """Bridge to EVEZ Lord.exe / LORD module. Provides entropy to OpenClawEngine."""

    def __init__(self, mode="auto"):
        # mode: auto | lord | sim
        self.mode = mode
        self._lord_available = LORD_STATE_FILE.exists()
        self._sim_entropy = 1.0
        print(f"[LordBridge] mode={mode} lord_available={self._lord_available}")

    def get_entropy(self, iteration: int) -> float:
        if self.mode == "lord" or (self.mode == "auto" and self._lord_available):
            return self._read_lord_entropy()
        return self._sim_entropy_decay(iteration)

    def _read_lord_entropy(self) -> float:
        try:
            with open(LORD_STATE_FILE) as f:
                data = json.load(f)
            return max(0.0, min(1.0, float(data.get("quantum_entropy", data.get("entropy", 1.0)))))
        except Exception as e:
            print(f"[LordBridge] Read error: {e}, using sim entropy")
            return self._sim_entropy

    def _sim_entropy_decay(self, iteration: int) -> float:
        """Exponential decay with noise. Converges ~iter 150-250."""
        self._sim_entropy = max(0.0, math.exp(-ENTROPY_DECAY_RATE * iteration) + random.gauss(0, 0.01))
        return self._sim_entropy

    def inject_lord_event(self, event_type: str, payload: dict = None):
        """Inject LORD event: entropy_pulse | resonance_lock | consciousness_shift"""
        if event_type == "entropy_pulse":
            delta = payload.get("delta", -0.05) if payload else -0.05
            self._sim_entropy = max(0.0, self._sim_entropy + delta)
        elif event_type == "resonance_lock":
            self._sim_entropy = 0.05  # Force TIER_3 proximity
        return self._sim_entropy

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "lord_available": self._lord_available,
            "sim_entropy": self._sim_entropy,
        }
