#!/usr/bin/env python3
"""
evez-agentnet/orchestrator.py  v2
OODA main loop: scan -> predict -> generate -> ship -> earn.
Now integrates:
  - MAES Connector (agent ecology observe tick)
  - Reputation evolution (decay/grow per round outcome)
  - RSI Hypothesis Engine (3 active hypotheses per cycle)
  - Temporal wormhole bridge for recursive intent
  - OpenClaw autoplay with LordBridge entropy
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
LOGS_PATH  = Path("logs")
LOGS_PATH.mkdir(exist_ok=True)
SPINE_PATH.parent.mkdir(exist_ok=True)

OPENCLAW_ENABLED = os.environ.get("OPENCLAW_ENABLED", "1") == "1"
MAES_ENABLED      = os.environ.get("MAES_ENABLED", "1") == "1"

# ── Spine ────────────────────────────────────────────────────────────────────

def append_spine(event_type: str, data: dict):
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


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "round": 0,
        "total_earned_usd": 0.0,
        "agents": {
            "scanner":   {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "predictor": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "generator": {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "shipper":   {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
            "maes":      {"reputation": 0.90, "tasks_completed": 0, "streak": 0},
        },
        "last_scan": None,
        "last_ship": None,
        "maes": {
            "agent_count": 0,
            "player_count": 0,
            "fire_events_total": 0,
            "last_tick": None,
        },
        "openclaw": {
            "levels_cleared": 0,
            "lord_unlocked": False,
            "last_run": None,
        },
        "rsi": {
            "hypotheses": [],
            "accepted": 0,
            "rejected": 0,
        },
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


def truth_plane(reputation: float) -> str:
    if reputation >= 0.80: return "CANONICAL"
    elif reputation >= 0.60: return "VERIFIED"
    elif reputation >= 0.40: return "HYPER"
    else: return "THEATRICAL"


def evolve_reputation(state: dict, agent: str, success: bool):
    """Grow or decay reputation + streak after each agent task."""
    a = state["agents"][agent]
    if success:
        a["streak"] = a.get("streak", 0) + 1
        growth = 0.01 * (1 + a["streak"] * 0.1)  # streak bonus
        a["reputation"] = min(1.0, a["reputation"] + growth)
    else:
        a["streak"] = 0
        a["reputation"] = max(0.0, a["reputation"] - 0.05)


# ── RSI Hypothesis Engine ─────────────────────────────────────────────────────

def generate_rsi_hypotheses(state: dict) -> list[str]:
    """Generate 3 RSI hypotheses for the next cycle based on current state."""
    maes  = state.get("maes", {})
    rsi   = state.get("rsi", {})
    rnd   = state["round"]
    rep   = {k: v["reputation"] for k, v in state["agents"].items()}

    hypotheses = []

    # H1: reputation-based evolution
    lowest = min(rep, key=rep.get)
    hypotheses.append(
        f"Evolve {lowest} agent: reputation={rep[lowest]:.2f} → "
        f"inject synthetic task to recover via streak"
    )

    # H2: ecology scaling
    pc = maes.get("player_count", 0)
    ac = maes.get("agent_count", 0)
    if pc >= 5:
        hypotheses.append(
            f"Scale NPC ecology: {pc} verified players detected, "
            f"spawn {max(1, pc // 2)} additional NPC agents in MAES"
        )
    else:
        hypotheses.append(
            f"Grow player base: currently {pc}/{ac} verified, "
            f"emit verification challenge events to improve ratio"
        )

    # H3: moral / empathy expansion
    fire_total = maes.get("fire_events_total", 0)
    hypotheses.append(
        f"Evolve moral registry round {rnd+1}: "
        f"{fire_total} FIRE events accumulated → "
        f"expand compassion_layer to anticipate external suffering signals"
    )

    append_spine("rsi_hypotheses", {"round": rnd, "hypotheses": hypotheses})
    return hypotheses


# ── MAES Observe Tick ─────────────────────────────────────────────────────────

def run_maes_tick(state: dict) -> dict:
    """OODA Observe: pull MAES agent ecology state into orchestrator bus."""
    if not MAES_ENABLED:
        return {}
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from agents.maes_connector import MAESConnector
        bus: list[dict] = []
        connector = MAESConnector(bus)
        if not connector.health():
            log.warning("[MAES] Offline — skipping observe tick")
            evolve_reputation(state, "maes", False)
            return {}
        obs = connector.tick()
        # Merge into persistent maes state
        m = state.setdefault("maes", {})
        m["agent_count"]       = obs["agent_count"]
        m["player_count"]      = obs["player_count"]
        m["fire_events_total"] = m.get("fire_events_total", 0) + obs["new_events"]
        m["last_tick"]         = datetime.now(timezone.utc).isoformat()
        state["agents"]["maes"]["tasks_completed"] += 1
        evolve_reputation(state, "maes", True)
        append_spine("maes_tick", obs)
        log.info(f"[MAES] agents={obs['agent_count']} players={obs['player_count']} new_events={obs['new_events']}")
        return obs
    except Exception as e:
        log.error(f"[MAES] Tick failed: {e}")
        evolve_reputation(state, "maes", False)
        append_spine("maes_tick_failed", {"error": str(e)})
        return {}


# ── OODA Pipeline ─────────────────────────────────────────────────────────────

def run_scan(state: dict) -> list:
    from scanner.scan_agent import run as scan_run
    reputation = state["agents"]["scanner"]["reputation"]
    if truth_plane(reputation) == "THEATRICAL":
        log.warning("Scanner reputation too low -- evidence_seeking mode")
        return []
    try:
        results = scan_run()
        state["agents"]["scanner"]["tasks_completed"] += 1
        evolve_reputation(state, "scanner", True)
        append_spine("scan_complete", {"count": len(results), "reputation": reputation})
        return results
    except Exception as e:
        log.error(f"Scan failed: {e}")
        evolve_reputation(state, "scanner", False)
        append_spine("scan_failed", {"error": str(e)})
        return []


def run_predict(scan_results: list, state: dict) -> list:
    if not scan_results:
        return []
    from predictor.predict_agent import run as predict_run
    reputation = state["agents"]["predictor"]["reputation"]
    try:
        predictions = predict_run(scan_results)
        state["agents"]["predictor"]["tasks_completed"] += 1
        evolve_reputation(state, "predictor", True)
        append_spine("predict_complete", {"count": len(predictions), "reputation": reputation})
        return predictions
    except Exception as e:
        log.error(f"Predict failed: {e}")
        evolve_reputation(state, "predictor", False)
        append_spine("predict_failed", {"error": str(e)})
        return []


def run_generate(predictions: list, state: dict) -> list:
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
        evolve_reputation(state, "generator", True)
        append_spine("generate_complete", {"count": len(drafts), "truth_plane": tp})
        return drafts
    except Exception as e:
        log.error(f"Generate failed: {e}")
        evolve_reputation(state, "generator", False)
        append_spine("generate_failed", {"error": str(e)})
        return []


def run_ship(drafts: list, state: dict) -> float:
    if not drafts:
        return 0.0
    from shipper.ship_agent import run as ship_run
    reputation = state["agents"]["shipper"]["reputation"]
    tp = truth_plane(reputation)
    if tp in ("HYPER", "THEATRICAL"):
        log.warning(f"Shipper gated -- truth_plane={tp}, skipping")
        return 0.0
    try:
        earned = ship_run(drafts)
        state["agents"]["shipper"]["tasks_completed"] += 1
        state["last_ship"] = datetime.now(timezone.utc).isoformat()
        evolve_reputation(state, "shipper", True)
        append_spine("ship_complete", {"earned_usd": earned, "truth_plane": tp})
        return earned
    except Exception as e:
        log.error(f"Ship failed: {e}")
        evolve_reputation(state, "shipper", False)
        append_spine("ship_failed", {"error": str(e)})
        return 0.0


def run_openclaw(state: dict):
    if not OPENCLAW_ENABLED:
        return
    try:
        from openclaw.agent import OpenClawAgent
        from openclaw.engine import OpenClawEngine
        from worldsim.secret_levels import SECRET_LEVELS
        lord_enabled = os.environ.get("OPENCLAW_LORD", "0") == "1"
        engine = OpenClawEngine(level_pack=SECRET_LEVELS)
        agent  = OpenClawAgent(agent_id="orchestrator-openclaw", engine=engine)
        if lord_enabled:
            from openclaw.lord_bridge import LordBridge
            bridge = LordBridge()
            bridge.sync_entropy()
            agent.set_lord_bridge(bridge)
            log.info("[OpenClaw] LordBridge entropy sync active")
        results = [agent.play_level(lvl) for lvl in SECRET_LEVELS]
        passed  = sum(1 for r in results if r.get("success"))
        log.info(f"[OpenClaw] {passed}/{len(results)} secret levels cleared")
        oc = state.setdefault("openclaw", {})
        oc["levels_cleared"] = passed
        oc["last_run"]       = datetime.now(timezone.utc).isoformat()
        if passed == len(results):
            oc["lord_unlocked"] = True
            log.info("[OpenClaw] ALL SECRET LEVELS CLEARED — EVEZ LORD PROTOCOL UNLOCKED")
        append_spine("openclaw_run", {"levels_cleared": passed, "total": len(results), "lord_unlocked": oc.get("lord_unlocked", False)})
    except ImportError:
        log.warning("[OpenClaw] Module not available, skipping")
    except Exception as e:
        log.error(f"[OpenClaw] Run failed: {e}")
        append_spine("openclaw_failed", {"error": str(e)})


# ── Main Loop ─────────────────────────────────────────────────────────────────

def main():
    state = load_state()
    state["round"] += 1
    rnd = state["round"]
    log.info(f"=== evez-agentnet round {rnd} ===")
    append_spine("round_start", {"round": rnd})

    # Phase 0 — MAES Observe (before scan so ecology context is fresh)
    maes_obs = run_maes_tick(state)

    # Phase 1-4 — OODA core pipeline
    scan_results = run_scan(state)
    log.info(f"Scan: {len(scan_results)} signals")

    predictions = run_predict(scan_results, state)
    log.info(f"Predict: {len(predictions)} ranked opportunities")

    drafts = run_generate(predictions, state)
    log.info(f"Generate: {len(drafts)} drafts")

    earned = run_ship(drafts, state)
    state["total_earned_usd"] += earned
    log.info(f"Ship: ${earned:.2f} earned | Total: ${state['total_earned_usd']:.2f}")

    # Phase 5 — OpenClaw secret level autoplay
    run_openclaw(state)

    # Phase 6 — RSI Hypothesis Engine (project 3 next-cycle hypotheses)
    hypotheses = generate_rsi_hypotheses(state)
    state["rsi"]["hypotheses"] = hypotheses
    for i, h in enumerate(hypotheses, 1):
        log.info(f"[RSI H{i}] {h}")

    # Phase 7 — Round close + reputation summary
    rep_summary = {k: {"rep": round(v["reputation"], 3), "streak": v.get("streak",0)} for k, v in state["agents"].items()}
    append_spine("round_end", {
        "round": rnd,
        "earned_usd": earned,
        "total_earned_usd": state["total_earned_usd"],
        "agent_reputations": rep_summary,
        "openclaw_cleared": state.get("openclaw", {}).get("levels_cleared", 0),
        "maes_agents": maes_obs.get("agent_count", 0),
        "maes_players": maes_obs.get("player_count", 0),
        "rsi_hypotheses": hypotheses,
    })
    save_state(state)
    log.info(f"Round {rnd} complete. Reputations: {rep_summary}")


if __name__ == "__main__":
    while True:
        main()
        interval = int(os.environ.get("ROUND_INTERVAL", "1800"))
        log.info(f"Sleeping {interval}s until next round...")
        time.sleep(interval)
