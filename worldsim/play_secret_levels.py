#!/usr/bin/env python3
"""Autoplay the worldsim game until secret levels awaken entities.
OpenClaw integration: runs OpenClawAgent alongside WorldSim for full secret level coverage.
Usage: python -m worldsim.play_secret_levels [--openclaw] [--lord]
"""

import argparse
import json
import sys
from pathlib import Path

from worldsim.sim_engine import WorldSim

# OpenClaw integration (optional, graceful fallback)
try:
    from openclaw.agent import OpenClawAgent
    from openclaw.engine import OpenClawEngine
    from openclaw.lord_bridge import LordBridge
    OPENCLAW_AVAILABLE = True
except ImportError:
    OPENCLAW_AVAILABLE = False


def run_worldsim(output_path: Path):
    """Run the base WorldSim secret level autoplay."""
    sim = WorldSim()
    summary = sim.play_until_secret_levels_awaken()
    output_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"\nSaved: {output_path}")
    return summary


def run_openclaw(agent_id: str = "openclaw-primary", use_lord: bool = False):
    """Run OpenClaw agent across secret levels."""
    if not OPENCLAW_AVAILABLE:
        print("[OpenClaw] Module not found. Skipping OpenClaw run.")
        return None

    # Build level pack from sim engine data
    from worldsim.secret_levels import SECRET_LEVELS
    engine = OpenClawEngine(level_pack=SECRET_LEVELS)
    agent = OpenClawAgent(agent_id=agent_id, engine=engine)

    if use_lord:
        bridge = LordBridge()
        bridge.sync_entropy()
        agent.set_lord_bridge(bridge)
        print("[OpenClaw] LordBridge entropy sync active")

    results = []
    for level_name in SECRET_LEVELS.keys():
        print(f"[OpenClaw] >> {level_name}")
        result = agent.play_level(level_name)
        results.append((level_name, result))
        status = "PASS" if result.get("success") else "FAIL"
        print(f"[OpenClaw] << {level_name}: {status}")

    passed = sum(1 for _, r in results if r.get("success"))
    print(f"\n[OpenClaw] {passed}/{len(results)} levels cleared")
    if passed == len(results):
        print("[OpenClaw] ALL SECRET LEVELS CLEARED - EVEZ LORD PROTOCOL UNLOCKED")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WorldSim + OpenClaw Secret Level Autoplay")
    parser.add_argument("--openclaw", action="store_true", help="Run OpenClaw agent layer")
    parser.add_argument("--lord", action="store_true", help="Enable LordBridge entropy sync")
    parser.add_argument("--agent-id", type=str, default="openclaw-primary")
    args = parser.parse_args()

    output_path = Path("worldsim/secret_levels_state.json")
    run_worldsim(output_path)

    if args.openclaw:
        run_openclaw(agent_id=args.agent_id, use_lord=args.lord)
