#!/usr/bin/env python3
"""Governed cognition-first orchestrator for evez-agentnet.

This is the strongest current entrypoint:
- LivingLogicDaemon after scan
- cognition-aware predictor with uncertainty ledger
- cognition-aware generator with build queue priority
- cognition-governed shipper using action_mode, unresolved residue, and entropy
- RSI branch injection before round close
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from cognition.checkpoint import CheckpointStore
from cognition.daemon import LivingLogicDaemon
from cognition.rsi_branch_injection import inject_rsi_hypotheses
from predictor.cognition_predict_agent import run as predict_run
from generator.cognition_generate_agent import run as generate_run
from shipper.cognition_ship_agent import run as governed_ship_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agentnet-cognition-governed")

SPINE_PATH = Path("spine/spine.jsonl")
STATE_PATH = Path("worldsim/worldsim_state.json")
LOGS_PATH = Path("logs")
LOGS_PATH.mkdir(exist_ok=True)
SPINE_PATH.parent.mkdir(exist_ok=True)

OPENCLAW_ENABLED = os.environ.get("OPENCLAW_ENABLED", "1") == "1"
MAES_ENABLED = os.environ.get("MAES_ENABLED", "1") == "1"
COGNITION_STATE_DIR = os.environ.get("COGNITION_STATE_DIR", ".state")
_DAEMON_STORE = CheckpointStore(COGNITION_STATE_DIR)
_DAEMON = LivingLogicDaemon(_DAEMON_STORE)


def append_spine(event_type: str, data: dict):
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "type": event_type, "data": data}
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
            "scanner": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "predictor": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "generator": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "shipper": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "maes": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
        },
        "last_scan": None,
        "last_ship": None,
        "maes": {"agent_count": 0, "player_count": 0, "fire_events_total": 0, "last_tick": None},
        "openclaw": {"levels_cleared": 0, "lord_unlocked": False, "last_run": None},
        "rsi": {"hypotheses": [], "accepted": 0, "rejected": 0},
        "temporal_wormhole": {
            "source": "meta-orchestrator",
            "destination": "meta-orchestrator",
            "purpose": "Bridge past-present-future for recursive intent",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def save_state(state: dict):
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def evolve_reputation(state: dict, agent: str, success: bool):
    a = state["agents"][agent]
    if success:
        a["streak"] = a.get("streak", 0) + 1
        growth = 0.01 * (1 + a["streak"] * 0.1)
        a["reputation"] = min(1.0, a["reputation"] + growth)
    else:
        a["streak"] = 0
        a["reputation"] = max(0.0, a["reputation"] - 0.05)


def truth_plane(reputation: float) -> str:
    if reputation >= 0.80:
        return "CANONICAL"
    if reputation >= 0.60:
        return "VERIFIED"
    if reputation >= 0.40:
        return "HYPER"
    return "THEATRICAL"


def summarize_scan(scan_results: list, maes_obs: dict, round_no: int) -> str:
    payload = {
        "round": round_no,
        "signal_count": len(scan_results),
        "maes_agents": maes_obs.get("agent_count", 0),
        "maes_players": maes_obs.get("player_count", 0),
        "top_signals": scan_results[:3],
    }
    return json.dumps(payload, ensure_ascii=False)


def generate_rsi_hypotheses(state: dict) -> list[str]:
    maes = state.get("maes", {})
    rnd = state["round"]
    rep = {k: v["reputation"] for k, v in state["agents"].items()}
    lowest = min(rep, key=rep.get)
    hypotheses = [f"Evolve {lowest} agent: reputation={rep[lowest]:.2f} -> inject synthetic task to recover via streak"]
    pc = maes.get("player_count", 0)
    ac = maes.get("agent_count", 0)
    if pc >= 5:
        hypotheses.append(f"Scale NPC ecology: {pc} verified players detected, spawn {max(1, pc // 2)} additional NPC agents in MAES")
    else:
        hypotheses.append(f"Grow player base: currently {pc}/{ac} verified, emit verification challenge events to improve ratio")
    fire_total = maes.get("fire_events_total", 0)
    hypotheses.append(f"Evolve moral registry round {rnd + 1}: {fire_total} FIRE events accumulated -> expand compassion_layer to anticipate external suffering signals")
    append_spine("rsi_hypotheses", {"round": rnd, "hypotheses": hypotheses})
    return hypotheses


def run_maes_tick(state: dict) -> dict:
    if not MAES_ENABLED:
        return {}
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from agents.maes_connector import MAESConnector
        bus: list[dict] = []
        connector = MAESConnector(bus)
        if not connector.health():
            evolve_reputation(state, "maes", False)
            return {}
        obs = connector.tick()
        m = state.setdefault("maes", {})
        m["agent_count"] = obs["agent_count"]
        m["player_count"] = obs["player_count"]
        m["fire_events_total"] = m.get("fire_events_total", 0) + obs["new_events"]
        m["last_tick"] = datetime.now(timezone.utc).isoformat()
        state["agents"]["maes"]["tasks_completed"] += 1
        evolve_reputation(state, "maes", True)
        append_spine("maes_tick", obs)
        return obs
    except Exception as e:
        evolve_reputation(state, "maes", False)
        append_spine("maes_tick_failed", {"error": str(e)})
        return {}


def run_scan(state: dict) -> list:
    from scanner.scan_agent import run as scan_run
    if truth_plane(state["agents"]["scanner"]["reputation"]) == "THEATRICAL":
        return []
    try:
        results = scan_run()
        state["agents"]["scanner"]["tasks_completed"] += 1
        evolve_reputation(state, "scanner", True)
        append_spine("scan_complete", {"count": len(results), "reputation": state["agents"]["scanner"]["reputation"]})
        return results
    except Exception as e:
        evolve_reputation(state, "scanner", False)
        append_spine("scan_failed", {"error": str(e)})
        return []


def run_openclaw(state: dict):
    if not OPENCLAW_ENABLED:
        return
    try:
        from openclaw.agent import OpenClawAgent
        from openclaw.engine import OpenClawEngine
        from worldsim.secret_levels import SECRET_LEVELS
        lord_enabled = os.environ.get("OPENCLAW_LORD", "0") == "1"
        engine = OpenClawEngine(level_pack=SECRET_LEVELS)
        agent = OpenClawAgent(agent_id="orchestrator-openclaw", engine=engine)
        if lord_enabled:
            from openclaw.lord_bridge import LordBridge
            bridge = LordBridge()
            bridge.sync_entropy()
            agent.set_lord_bridge(bridge)
        results = [agent.play_level(lvl) for lvl in SECRET_LEVELS]
        passed = sum(1 for r in results if r.get("success"))
        oc = state.setdefault("openclaw", {})
        oc["levels_cleared"] = passed
        oc["last_run"] = datetime.now(timezone.utc).isoformat()
        if passed == len(results):
            oc["lord_unlocked"] = True
        append_spine("openclaw_run", {"levels_cleared": passed, "total": len(results), "lord_unlocked": oc.get("lord_unlocked", False)})
    except Exception as e:
        append_spine("openclaw_failed", {"error": str(e)})


def main():
    state = load_state()
    state["round"] += 1
    rnd = state["round"]
    append_spine("round_start", {"round": rnd, "mode": "cognition_governed"})

    maes_obs = run_maes_tick(state)
    scan_results = run_scan(state)
    daemon_state = _DAEMON.step(summarize_scan(scan_results, maes_obs, rnd))
    append_spine("cognition_step", {
        "round": rnd,
        "active_identity": daemon_state["active_identity"],
        "action_mode": daemon_state["action_mode"],
        "checkpoint": daemon_state["checkpoint"],
        "lineage_hash": daemon_state["lineage_hash"],
        "unresolved_count": daemon_state["revision"].get("unresolved_count", 0),
        "dark_pressure_count": daemon_state["revision"].get("dark_pressure_count", 0),
    })

    prediction_packet = predict_run(scan_results)
    predictions = prediction_packet.get("ranked", [])
    uncertainty = prediction_packet.get("uncertainty", {})
    predictor_entropy = float(uncertainty.get("entropy", 0.0) or 0.0)
    _DAEMON.state.self_model["predictor_entropy"] = predictor_entropy
    append_spine("predict_complete", {
        "round": rnd,
        "count": len(predictions),
        "entropy": predictor_entropy,
        "rival_count": uncertainty.get("rival_count", 0),
        "top_rivals": uncertainty.get("top_rivals", []),
    })

    if predictor_entropy >= 1.2:
        _DAEMON.state.unresolved_residue.append(f"predictor_entropy:{predictor_entropy}")
        _DAEMON.state.self_model["action_mode"] = "evidence_seek"
        append_spine("cognition_gate", {"round": rnd, "gate": "predictor_entropy", "entropy": predictor_entropy})

    drafts = generate_run(predictions, truth_plane=truth_plane(state["agents"]["generator"]["reputation"]))
    state["agents"]["generator"]["tasks_completed"] += 1
    evolve_reputation(state, "generator", True)
    append_spine("generate_complete", {"round": rnd, "count": len(drafts), "action_mode": _DAEMON.state.self_model.get("action_mode")})

    earned, ship_gate = governed_ship_run(
        drafts,
        action_mode=_DAEMON.state.self_model.get("action_mode", daemon_state["action_mode"]),
        unresolved_count=len(_DAEMON.state.unresolved_residue),
        predictor_entropy=predictor_entropy,
        lineage_hash=_DAEMON.last_hash,
    )
    state["total_earned_usd"] += earned
    append_spine("ship_governance", {"round": rnd, **ship_gate})

    if ship_gate.get("status") == "shipped":
        state["agents"]["shipper"]["tasks_completed"] += 1
        evolve_reputation(state, "shipper", True)
    else:
        evolve_reputation(state, "shipper", False)

    run_openclaw(state)

    hypotheses = generate_rsi_hypotheses(state)
    state["rsi"]["hypotheses"] = hypotheses
    injection = inject_rsi_hypotheses(_DAEMON, hypotheses, rnd)
    checkpoint_path = _DAEMON.checkpoint()
    append_spine("rsi_branch_injection", {
        "round": rnd,
        "checkpoint": checkpoint_path,
        "lineage_hash": _DAEMON.last_hash,
        "hypothesis_count": injection["hypothesis_count"],
        "entropy": injection["entropy"],
        "unresolved_count": injection["unresolved_count"],
        "dark_pressure_count": injection["dark_pressure_count"],
    })

    rep_summary = {k: {"rep": round(v["reputation"], 3), "streak": v.get("streak", 0)} for k, v in state["agents"].items()}
    append_spine("round_end", {
        "round": rnd,
        "mode": "cognition_governed",
        "earned_usd": earned,
        "total_earned_usd": state["total_earned_usd"],
        "agent_reputations": rep_summary,
        "active_identity": _DAEMON.state.self_model["active_identity"],
        "action_mode": _DAEMON.state.self_model.get("action_mode", "hold"),
        "predictor_entropy": _DAEMON.state.self_model.get("predictor_entropy"),
        "rsi_branch_entropy": _DAEMON.state.self_model.get("rsi_branch_entropy"),
        "rsi_hypotheses": hypotheses,
    })
    save_state(state)


if __name__ == "__main__":
    while True:
        main()
        interval = int(os.environ.get("ROUND_INTERVAL", "1800"))
        log.info("Sleeping %ss until next cognition-governed round...", interval)
        time.sleep(interval)
