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
    """Append one hash-chained entry.

    Chain: each entry commits to the previous entry's hash, and carries a
    monotonic sequence number. Per-entry hashing alone does NOT detect
    truncation, reordering, or a fully re-hashed forgery — this does. See
    test_evidence_falsification.py for the attack it defends against.
    """
    seq, prev = _spine_tail()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "seq": seq + 1,
        "type": event_type,
        "data": data,
    }
    if prev:
        entry["prev_sha256"] = prev
    entry_str = json.dumps(entry, sort_keys=True)
    entry["sha256"] = hashlib.sha256(entry_str.encode()).hexdigest()[:16]
    with open(SPINE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _spine_tail():
    """Return (last_seq, last_sha256) without loading the whole spine."""
    last_seq, last_sha = 0, ""
    try:
        with open(SPINE_PATH, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            # read the last ~64KB, enough for one line
            f.seek(max(0, size - 65536))
            chunk = f.read().decode("utf-8", "replace")
    except FileNotFoundError:
        return 0, ""
    for line in reversed(chunk.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        return e.get("seq", 0), e.get("sha256", "")
    return 0, ""


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

def _stuck_agents(rep: dict, tasks: dict) -> list[tuple]:
    """Agents that are saturated at 1.0 reputation but not producing anything.

    The old logic picked min(reputation) unconditionally. Once every agent hit
    the 1.0 ceiling (which happens within ~10 healthy rounds) it always selected
    whichever name sorted first and emitted "recover via streak" — advice to a
    perfect agent. What is actually actionable is a HIGH-reputation agent whose
    task counter is flat: that one is succeeding without doing more work.
    """
    stuck = []
    for name, rv in rep.items():
        if rv >= 0.99 and tasks.get(name, 0) == 0:
            stuck.append((name, rv))
    return stuck


def generate_rsi_hypotheses(state: dict) -> list[dict]:
    """Generate 3 RSI hypotheses for the next cycle based on current state.

    Returns structured directives, not prose. Each carries `action` (a key the
    gate in apply_rsi_directives() can consume) so a hypothesis can actually
    change behaviour instead of being logged and forgotten.
    """
    maes  = state.get("maes", {})
    rnd   = state["round"]
    rep   = {k: v["reputation"] for k, v in state["agents"].items()}
    tasks = {k: v.get("tasks_completed", 0) for k, v in state["agents"].items()}

    hypotheses = []
    stuck = _stuck_agents(rep, tasks)

    # H1: reputation-based evolution
    if stuck:
        name, rv = stuck[0]
        hypotheses.append({
            "id": "H1",
            "action": "raise_scan_yield",
            "agent": name,
            "text": (f"{name} is saturated at reputation={rv:.2f} with 0 tasks "
                     f"completed — raise scan yield instead of chasing reputation"),
        })
    else:
        # Genuinely pick the weakest, and only if it is actually below par.
        lowest = min(rep, key=rep.get)
        if rep[lowest] < 0.95:
            hypotheses.append({
                "id": "H1",
                "action": "recover_reputation",
                "agent": lowest,
                "text": (f"{lowest} reputation={rep[lowest]:.2f} below par → "
                         f"inject synthetic task to recover via streak"),
            })
        else:
            hypotheses.append({
                "id": "H1",
                "action": "hold",
                "agent": None,
                "text": f"All agents at or above par (min={min(rep.values()):.2f}) — hold steady",
            })

    # H2: ecology scaling
    pc = maes.get("player_count", 0)
    ac = maes.get("agent_count", 0)
    if pc >= 5:
        hypotheses.append({
            "id": "H2",
            "action": "spawn_npcs",
            "agent": None,
            "text": (f"Scale NPC ecology: {pc} verified players detected, "
                     f"spawn {max(1, pc // 2)} additional NPC agents in MAES"),
        })
    elif ac > 0:
        hypotheses.append({
            "id": "H2",
            "action": "emit_verification",
            "agent": None,
            "text": (f"Grow player base: currently {pc}/{ac} verified "
                     f"({pc/ac:.0%}) — emit verification challenge events"),
        })
    else:
        hypotheses.append({
            "id": "H2", "action": "wait_for_ecology", "agent": None,
            "text": "MAES ecology empty — no players or agents to scale yet",
        })

    # H3: moral / empathy expansion
    # The old branch said "expand compassion_layer" when fire_total was 0,
    # which is backwards: zero signal means hold, not widen the aperture.
    fire_total = maes.get("fire_events_total", 0)
    if fire_total == 0:
        hypotheses.append({
            "id": "H3",
            "action": "hold",
            "agent": None,
            "text": f"Moral registry round {rnd+1}: 0 FIRE events — hold compassion_layer, no signal to act on",
        })
    else:
        hypotheses.append({
            "id": "H3",
            "action": "expand_compassion",
            "agent": None,
            "text": (f"Moral registry round {rnd+1}: {fire_total} FIRE events "
                     f"accumulated → expand compassion_layer to anticipate "
                     f"external suffering signals"),
        })

    append_spine("rsi_hypotheses", {"round": rnd, "hypotheses": hypotheses})
    return hypotheses


def apply_rsi_directives(state: dict, hypotheses: list[dict]) -> list[str]:
    """Consume the previous cycle's directives. This is the gate that makes
    hypotheses non-decorative: without it, generate_rsi_hypotheses() only ever
    wrote strings to the spine that nothing downstream read.

    Returns the list of directive keys that actually changed state.
    """
    applied = []
    for h in hypotheses:
        # State written by earlier versions holds bare strings, not dicts.
        # Skip them rather than crashing the round on a legacy record.
        if not isinstance(h, dict):
            log.warning(f"[RSI] skipping legacy hypothesis format: {str(h)[:60]}")
            continue
        act = h.get("action")
        if act == "raise_scan_yield":
            # Widen the scanner's net so a saturated agent produces more signal.
            state["scan"]["yield_multiplier"] = min(
                3.0, state.setdefault("scan", {}).get("yield_multiplier", 1.0) + 0.25)
            applied.append("raise_scan_yield")
        elif act == "spawn_npcs":
            maes = state.setdefault("maes", {})
            maes["pending_npc_spawn"] = maes.get("pending_npc_spawn", 0) + \
                max(1, maes.get("player_count", 0) // 2)
            applied.append("spawn_npcs")
        elif act == "expand_compassion":
            maes = state.setdefault("maes", {})
            maes["compassion_expansion"] = maes.get("compassion_expansion", 0) + 1
            applied.append("expand_compassion")
        elif act == "recover_reputation":
            name = h.get("agent")
            if name in state.get("agents", {}):
                # Reset the streak so the next success pays the base rate again.
                state["agents"][name]["streak"] = 0
                applied.append("recover_reputation")
    if applied:
        append_spine("rsi_directives_applied", {"round": state["round"], "applied": applied})
    return applied


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
        # An RSI directive may ask for a wider net when reputation saturates.
        mult = state.get("scan", {}).get("yield_multiplier", 1.0)
        if mult > 1.0 and results:
            keep = max(1, int(len(results) * mult))
            if keep > len(results):
                pool = [r for r in results if isinstance(r, dict)]
                # results are already ranked; top up from the remaining pool
                results = results + pool[len(results):keep]
            results = results[:keep]
            log.info(f"Scan: yield_multiplier={mult:.2f} -> {len(results)} signals")
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
    """Publish drafts and return verified revenue.

    The shipper now returns a summary dict with the REASON each draft did or
    did not reach a channel, because "Shipped" was previously logged for drafts
    that never left the machine. Reputation now evolves on what actually
    shipped, so the agent cannot coast on fake successes forever.
    """
    if not drafts:
        return 0.0
    from shipper.ship_agent import run as ship_run
    reputation = state["agents"]["shipper"]["reputation"]
    tp = truth_plane(reputation)
    if tp in ("HYPER", "THEATRICAL"):
        log.warning("Shipper gated -- truth_plane=%s, skipping", tp)
        return 0.0
    try:
        summary = ship_run(drafts)
        # Older shipper returned a bare float; keep both paths working.
        if isinstance(summary, (int, float)):
            summary = {"attempted": len(drafts), "shipped": len(drafts),
                       "earned_usd": float(summary), "reasons": {}, "legacy": True}

        shipped = summary.get("shipped", 0)
        attempted = summary.get("attempted", 0)
        earned = float(summary.get("earned_usd", 0.0))

        state["agents"]["shipper"]["tasks_completed"] += 1
        if shipped:
            state["last_ship"] = datetime.now(timezone.utc).isoformat()
        evolve_reputation(state, "shipper", shipped > 0)

        reasons = dict(summary.get("reasons") or {})
        append_spine("ship_complete", {
            "earned_usd": earned,
            "truth_plane": tp,
            "attempted": attempted,
            "shipped": shipped,
            "not_shipped_reasons": reasons,
            "channels_available": summary.get("channels_available", []),
        })

        if attempted and not shipped:
            top = max(reasons.items(), key=lambda kv: kv[1])[0] if reasons else "unknown"
            log.warning("Shipper: 0/%d delivered (most common: %s). "
                        "Drafts are being produced but not published.",
                        attempted, top)
        return earned
    except Exception as e:
        log.error("Ship failed: %s", e)
        evolve_reputation(state, "shipper", False)
        append_spine("ship_failed", {"error": str(e)})
        return 0.0


def run_openclaw(state: dict):
    if not OPENCLAW_ENABLED:
        return
    oc = state.setdefault("openclaw", {})
    if oc.get("broken"):
        log.warning("[OpenClaw] Module marked broken (previous failure), skipping this round")
        return
    try:
        from openclaw.agent import OpenClawAgent
        from openclaw.engine import OpenClawEngine
        from worldsim.secret_levels import SECRET_LEVELS
        lord_enabled = os.environ.get("OPENCLAW_LORD", "0") == "1"
        engine = OpenClawEngine()
        agent  = OpenClawAgent()
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
        log.error(f"[OpenClaw] Run FAILED — module marked broken for subsequent rounds: {e}")
        oc["broken"] = True
        oc["broken_at"] = datetime.now(timezone.utc).isoformat()
        oc["broken_error"] = str(e)
        append_spine("openclaw_broken", {"error": str(e), "broken_at": oc["broken_at"]})
        oc.pop("levels_cleared", None)
        oc.pop("last_run", None)


# ── Main Loop ─────────────────────────────────────────────────────────────────

def main():
    state = load_state()
    state["round"] += 1
    rnd = state["round"]
    log.info(f"=== evez-agentnet round {rnd} ===")
    append_spine("round_start", {"round": rnd})

    # Phase 0 — apply last cycle's directives BEFORE anything reads state, so the
    # RSI engine has an actual effect on this round rather than only annotating it.
    prev = state.get("rsi", {}).get("hypotheses", [])
    if prev:
        applied = apply_rsi_directives(state, prev)
        log.info(f"[RSI] applied {len(applied)} directive(s) from round {rnd-1}: {applied}")

    # Phase 0b — MAES Observe (before scan so ecology context is fresh)
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

    # Phase 5.5 — JEV System One advice (advisory; never overrides)
    try:
        import jev_integration as JEV
        advice = JEV.advise(state, rnd)
        log.info("[JEV] %s", JEV.summarise(advice))
        state.setdefault("jev", {})["last_advice"] = {
            "round": rnd,
            "available": advice.get("available"),
            "agreement": advice.get("agreement", {}),
        }
    except Exception as e:
        # JEV must never break the pipeline, whatever it does.
        log.warning("[JEV] integration skipped: %s", str(e)[:120])

    # Phase 6 — RSI Hypothesis Engine (project 3 next-cycle hypotheses)
    hypotheses = generate_rsi_hypotheses(state)
    state["rsi"]["hypotheses"] = hypotheses
    for i, h in enumerate(hypotheses, 1):
        log.info(f"[RSI {h.get('id','?')}/{h.get('action','?')}] {h.get('text', h)}")

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
