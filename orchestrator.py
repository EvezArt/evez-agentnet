#!/usr/bin/env python3
"""
evez-agentnet/orchestrator.py
Main loop: scan -> predict -> generate -> ship -> earn.
Runs every 30 min. Built on EVEZ-OS spine provenance.
Creator: Steven Crawford-Maggard (EVEZ666)
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agentnet")

SPINE_PATH = Path("spine/spine.jsonl")
STATE_PATH = Path("worldsim/worldsim_state.json")
LOGS_PATH = Path("logs")
LOGS_PATH.mkdir(exist_ok=True)
SPINE_PATH.parent.mkdir(exist_ok=True)


def append_spine(event_type: str, data: dict):
    """Append event to spine.jsonl with sha256 hash chain."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "data": data,
    }
    entry_str = json.dumps(entry, sort_keys=True)
    entry["sha256"] = hashlib.sha256(entry_str.encode()).hexdigest()[:16]
    with open(SPINE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "round": 0,
        "total_earned_usd": 0.0,
        "agents": {
            "scanner": {"reputation": 0.90, "tasks_completed": 0},
            "predictor": {"reputation": 0.90, "tasks_completed": 0},
            "generator": {"reputation": 0.90, "tasks_completed": 0},
            "shipper": {"reputation": 0.90, "tasks_completed": 0},
        },
        "last_scan": None,
        "last_ship": None,
    }


def save_state(state: dict):
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def truth_plane(reputation: float) -> str:
    if reputation >= 0.80: return "CANONICAL"
    elif reputation >= 0.60: return "VERIFIED"
    elif reputation >= 0.40: return "HYPER"
    else: return "THEATRICAL"


def run_scan(state: dict) -> list:
    """Scanner agent: pull live signals from configured sources."""
    from scanner.scan_agent import run as scan_run
    reputation = state["agents"]["scanner"]["reputation"]
    if truth_plane(reputation) == "THEATRICAL":
        log.warning("Scanner reputation too low -- evidence_seeking mode")
        return []
    try:
        results = scan_run()
        state["agents"]["scanner"]["tasks_completed"] += 1
        append_spine("scan_complete", {"count": len(results), "reputation": reputation})
        return results
    except Exception as e:
        log.error(f"Scan failed: {e}")
        state["agents"]["scanner"]["reputation"] = max(0.0, reputation - 0.05)
        append_spine("scan_failed", {"error": str(e)})
        return []


def run_predict(scan_results: list, state: dict) -> list:
    """Predictor agent: rank + synthesize scan results."""
    if not scan_results:
        return []
    from predictor.predict_agent import run as predict_run
    reputation = state["agents"]["predictor"]["reputation"]
    try:
        predictions = predict_run(scan_results)
        state["agents"]["predictor"]["tasks_completed"] += 1
        append_spine("predict_complete", {"count": len(predictions), "reputation": reputation})
        return predictions
    except Exception as e:
        log.error(f"Predict failed: {e}")
        state["agents"]["predictor"]["reputation"] = max(0.0, reputation - 0.05)
        append_spine("predict_failed", {"error": str(e)})
        return []


def run_generate(predictions: list, state: dict) -> list:
    """Generator agent: draft deliverables from top predictions."""
    if not predictions:
        return []
    from generator.generate_agent import run as gen_run
    reputation = state["agents"]["generator"]["reputation"]
    tp = truth_plane(reputation)
    if tp == "THEATRICAL":
        log.warning("Generator blocked -- reputation below threshold")
        return []
    try:
        drafts = gen_run(predictions, truth_plane=tp)
        state["agents"]["generator"]["tasks_completed"] += 1
        append_spine("generate_complete", {"count": len(drafts), "truth_plane": tp})
        return drafts
    except Exception as e:
        log.error(f"Generate failed: {e}")
        state["agents"]["generator"]["reputation"] = max(0.0, reputation - 0.05)
        append_spine("generate_failed", {"error": str(e)})
        return []


def run_ship(drafts: list, state: dict) -> float:
    """Shipper agent: post approved drafts to Twitter/Gumroad/GitHub."""
    if not drafts:
        return 0.0
    from shipper.ship_agent import run as ship_run
    reputation = state["agents"]["shipper"]["reputation"]
    tp = truth_plane(reputation)
    # Require VERIFIED+ to ship
    if tp in ("HYPER", "THEATRICAL"):
        log.warning(f"Shipper gated -- truth_plane={tp}, skipping")
        return 0.0
    try:
        earned = ship_run(drafts)
        state["agents"]["shipper"]["tasks_completed"] += 1
        state["last_ship"] = datetime.now(timezone.utc).isoformat()
        append_spine("ship_complete", {"earned_usd": earned, "truth_plane": tp})
        return earned
    except Exception as e:
        log.error(f"Ship failed: {e}")
        state["agents"]["shipper"]["reputation"] = max(0.0, reputation - 0.05)
        append_spine("ship_failed", {"error": str(e)})
        return 0.0


def main():
    state = load_state()
    state["round"] += 1
    rnd = state["round"]
    log.info(f"=== evez-agentnet round {rnd} ===")
    append_spine("round_start", {"round": rnd})

    scan_results = run_scan(state)
    log.info(f"Scan: {len(scan_results)} signals")

    predictions = run_predict(scan_results, state)
    log.info(f"Predict: {len(predictions)} ranked opportunities")

    drafts = run_generate(predictions, state)
    log.info(f"Generate: {len(drafts)} drafts")

    earned = run_ship(drafts, state)
    state["total_earned_usd"] += earned
    log.info(f"Ship: ${earned:.2f} earned | Total: ${state['total_earned_usd']:.2f}")

    append_spine("round_end", {
        "round": rnd,
        "earned_usd": earned,
        "total_earned_usd": state["total_earned_usd"],
        "agent_reputations": {k: v["reputation"] for k, v in state["agents"].items()},
    })
    save_state(state)
    log.info(f"Round {rnd} complete.")


if __name__ == "__main__":
    main()
