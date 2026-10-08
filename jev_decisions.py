#!/usr/bin/env python3
"""
Jev-backed decision layer for evez-agentnet.

Where this helps, concretely: the RSI engine and the shipper both make
threshold decisions from hardcoded numbers (rep >= 0.99 saturated, rep < 0.95
recover, 0 delivered = warn). Those thresholds were the source of two real
defects this session: prescribing recovery to a perfect agent, and expanding
compassion on zero signal.

Jev evaluates the same question against real state and returns a CALIBRATED
probability plus confidence. That lets the system abstain when it is unsure,
which a hardcoded threshold cannot do.

Every decision records: the question asked, the probability, the confidence,
and whether the threshold was met. If Jev is unavailable the caller is told
so explicitly — this module never silently falls back to a guess, because a
fabricated probability is exactly the failure mode being fixed.

Enable with:  export TYPESAFE_API_KEY=...  (early access key from typesafe.ai)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from jev_client import JevUnavailable, evaluate

log = logging.getLogger("agentnet.jev")

JEV_ENABLED = os.environ.get("JEV_ENABLED", "1") == "1"
DECISION_LOG = Path("jev/decisions.jsonl")

# Abstain below this confidence. A 0.51 call on a 3-way choice is worse than
# no call at all, because code will branch on it either way.
MIN_CONFIDENCE = float(os.environ.get("JEV_MIN_CONFIDENCE", "0.55"))

# Probabilities at or above this count as "yes" for NouL questions (rug pull risk).
YES_THRESHOLD = 0.70

# Probabilities at or above this count as "yes" for Choice questions (buy/sell).
YES_THRESHOLD_CHOICE = 0.65

# Probabilities at or above this count as "yes" for Score questions (severity).
YES_THRESHOLD_SCORE = 0.60


def _record(entry: dict) -> None:
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    DECISION_LOG.parent.mkdir(exist_ok=True)
    with open(DECISION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── coin evaluation ──────────────────────────────────────────────────────────
def judge_coin_rug(state: dict) -> dict:
    """Ask Jev whether a new coin is likely a rug pull.

    Returns {noul: probability, verdict: True/False, confidence, threshold}.
    The crawler pre-filters 80/81 fakes; Jev provides the calibrated probability
    so the pipeline can abstain when unsure rather than guessing.
    """
    # Extract coin state from the agent's environment
    # Look for recent scanner signals or market data in the state
    rsi_hyps = state.get("rsi", {}).get("hypotheses", []) or []
    total_earned = state.get("total_earned_usd", 0.0)

    questions = {
        "rug_pull": {
            "type": "noul",
            "instructions": "Considering this new coin's launch pattern, liquidity lock, "
                           "community size, and developer transparency — what is the "
                           "probability this is a rug pull (creator can dump on buyers)? "
                           "Return a number in [0,1] where 1 = certain rug, 0 = certain not.",
            "criteria": {
                "true": "High rug probability: no liquidity lock, anonymous dev, zero supply "
                       "or extreme concentration, or known dump patterns",
                "false": "Low rug probability: audited contract, locked liquidity, known team, "
                        "reasonable tokenomics",
            },
        }
    }

    return _decide("coin_rug", state, questions,
                   fallback={"noul": 0.5, "verdict": "unknown"},
                   note="crawler pre-filtered 80/81 fakes; Jev provides calibrated probability")


def judge_coin_momentum(state: dict) -> dict:
    """Ask Jev whether a surviving coin has upward momentum.

    Returns {choice: "buy"/"sell"/"hold", probabilities, confidence, abstained}.
    This is the second gate after rug pull — Jev says yes on direction, not
    absolute price.
    """
    questions = {
        "direction": {
            "type": "choice",
            "instructions": "Given the price action observed over the last window, "
                           "which direction does this coin most likely move next? ",
            "criteria": {
                "buy": "Price likely to rise: buyers returning, higher lows, volume increase",
                "sell": "Price likely to fall: lower highs, declining volume, distribution",
                "hold": "Price direction unclear: range-bound, low volume, mixed signals",
            },
        }
    }

    return _decide("coin_momentum", state, questions,
                   fallback={"choice": "hold", "probabilities": {"buy": 0.33, "sell": 0.33, "hold": 0.34}},
                   note="second gate after rug filter; Jev calibrated direction not price")


def judge_coin_severity(state: dict) -> dict:
    """Ask Jev how severe a coin's condition is.

    Returns {score: 0-3, legend, probabilities, confidence}.
    0 = Healthy, 1 = Degraded, 2 = Broken, 3 = Rekt.
    """
    questions = {
        "severity": {
            "type": "score",
            "instructions": "Rate this coin's current condition on a scale of 0-3: "
                           "0 = Healthy (price stable, healthy holders), "
                           "1 = Degraded (some holders down, low volume), "
                           "2 = Broken (majority down 50%+), "
                           "3 = Rekt (majority down 80%+, essentially dead).",
            "criteria": [0, 1, 2, 3],
        }
    }

    return _decide("coin_severity", state, questions,
                   fallback={"score": 0, "legend": {"0": "Healthy", "1": "Degraded", "2": "Broken", "3": "Rkt"}, "probabilities": {"0": 1.0}},
                   note="condition assessment for position sizing")


def available() -> bool:
    return JEV_ENABLED and bool(os.environ.get("TYPESAFE_API_KEY", "").strip())


def _state_snapshot(state: dict) -> dict:
    """Compact, structured state — the format Jev is designed to consume."""
    agents = state.get("agents", {})
    maes = state.get("maes", {})
    return {
        "round": state.get("round"),
        "total_earned_usd": state.get("total_earned_usd", 0.0),
        "agents": {
            k: {"reputation": round(v.get("reputation", 0), 4),
                "tasks_completed": v.get("tasks_completed", 0),
                "streak": v.get("streak", 0)}
            for k, v in agents.items()
        },
        "maes": {
            "player_count": maes.get("player_count", 0),
            "agent_count": maes.get("agent_count", 0),
            "fire_events_total": maes.get("fire_events_total", 0),
        },
        "rsi_last": (state.get("rsi", {}) or {}).get("hypotheses", [])[:3],
    }


# ── decision 1: is the shipper genuinely stuck, or just unconfigured? ───────
def judge_shipper_health(state: dict) -> dict:
    """Distinguish 'broken' from 'no credentials' — two different repairs."""
    ship = _ship_log_tail()
    snap = _state_snapshot(state)
    snap["shipper_log_tail"] = ship

    questions = {
        "broken": {
            "type": "noul",
            "instructions": "Does this ship'sper have a delivery path that is "
                           "failing at runtime (errors, rate limits, rejected "
                           "payloads), rather than simply having no "
                           "credentialed transport configured?",
            "criteria": {
                "true": "Delivery attempts are failing with API errors",
                "false": "No channel is configured, or delivery is succeeding",
            },
        },
        "severity": {
            "type": "score",
            "instructions": "How severe is the shipper's current condition?",
            "criteria": [
                "Healthy — drafts are being delivered",
                "Idle — no channel configured, nothing lost",
                "Degraded — some deliveries failing",
                "Broken — every delivery failing",
            ],
        },
    }

    return _decide("shipper_health", snap, questions,
                   fallback="unknown", note="repairs differ: config vs bug")


# ── decision 2: which agent most needs attention? ──────────────────────────
def judge_attention_target(state: dict) -> dict:
    """Ask which single agent warrants intervention, with probabilities.

    Replaces `min(reputation)` — which on a saturated roster always returned
    the same name and produced nonsense directives for 244 rounds.
    """
    questions = {
        "target": {
            "type": "choice",
            "instructions": "Which agent most warrants intervention this cycle?",
            "criteria": {
                "none": "All agents are healthy; no intervention needed",
                "scanner": "The scanner is producing little or poor signal",
                "predictor": "The predictor is mis-ranking opportunities",
                "generator": "The generator is producing unusable drafts",
                "shipper": "The shipper is failing to deliver",
                "maes": "The ecology connector is offline or misreporting",
            },
        },
    }
    return _decide("attention_target", _state_snapshot(state), questions,
                   fallback="none")


# ── decision 3: should this cycle escalate to a human? ─────────────────────
def judge_escalation(brief_text: str, health_json: dict) -> dict:
    """Gate the Telegram alert on a calibrated judgement, not a keyword match."""
    state = {"brief": brief_text[:4000], "health": health_json}
    questions = {
        "escalate": {
            "type": "noul",
            "instructions": "Does this situation require human action now?",
            "criteria": {
                "true": "Credentials exposed, service down, or revenue blocked",
                "false": "Cosmetic, informational, or already known",
            },
        },
    }
    return _decide("escalation", state, questions, fallback="no")


# ── core ───────────────────────────────────────────────────────────────────
def _decide(name: str, state: dict, questions: dict, *, fallback: str | dict = "unknown",
            note: str = "") -> dict:
    if not available():
        fb = json.dumps(fallback) if isinstance(fallback, dict) else fallback
        _record({"decision": name, "result": "skipped",
                 "reason": "jev_disabled_or_no_key", "fallback": fb})
        return {"ok": False, "decision": name, "value": fb,
                "source": "fallback", "reason": "Jev unavailable (no key)"}

    try:
        answers = evaluate(state, questions)
    except JevUnavailable as e:
        fb = json.dumps(fallback) if isinstance(fallback, dict) else fallback
        _record({"decision": name, "result": "skipped",
                 "reason": str(e)[:200], "fallback": fb})
        return {"ok": False, "decision": name, "value": fb,
                "source": "fallback", "reason": str(e)[:200]}

    result = {"ok": True, "decision": name, "source": "jev", "note": note,
              "raw": {k: {"type": a.type, "noul": a.noul, "choice": a.choice,
                          "score": a.score, "confidence": a.confidence,
                          "probabilities": a.probabilities,
                          "model": a.model}
                      for k, a in answers.items()}}

    acted = False
    for key, a in answers.items():
        if a.type == "noul":
            value = (a.noul or 0.0) >= YES_THRESHOLD
            result[key] = {"probability": a.noul, "verdict": value,
                           "threshold": YES_THRESHOLD}
            acted = True
        elif a.type == "choice":
            conf = a.confidence or 0.0
            abstain = conf < MIN_CONFIDENCE
            result[key] = {
                "choice": None if abstain else a.choice,
                "probabilities": a.probabilities,
                "confidence": conf,
                "abstained": abstain,
                "min_confidence": MIN_CONFIDENCE,
            }
            acted = True
        elif a.type == "score":
            result[key] = {"score": a.score, "confidence": a.confidence,
                           "legend": a.legend,
                           "probabilities": a.probabilities}
            acted = True

    _record({"decision": name, "result": "answered", "detail": result.get("raw"),
             "confidence": {k: result[k].get("confidence")
                            for k in result if isinstance(result.get(k), dict)},
             "abstained": any(result[k].get("abstained")
                              for k in result if isinstance(result.get(k), dict))})

    # ── Append Jev decision hash to spine for attribution chain ──
    # Build a deterministic hash from the decision essentials so the spine
    # can cryptographically link the judgement to every subsequent spend.
    _decision_hash = hashlib.sha256(
        json.dumps({
            "name": name,
            "noul_probs": {k: v.get("probability") for k, v in result.items()
             if isinstance(v, dict) and "probability" in v},
            "choice": {k: v.get("choice") for k, v in result.items()
             if isinstance(v, dict) and "choice" in v},
            "score": {k: v.get("score") for k, v in result.items()
             if isinstance(v, dict) and "score" in v},
            "confidence": {k: v.get("confidence") for k, v in result.items()
             if isinstance(v, dict) and "confidence" in v},
        }, sort_keys=True).encode()
    ).hexdigest()[:16]
    from jev_integration import _append_spine  # sibling late-import: the seam
    _append_spine("jev_decision", {
        "decision": name,
        "hash": _decision_hash,
        "detail": result.get("raw"),
    }, jev_decision_hash=_decision_hash)
    return result


def _ship_log_tail(n: int = 25) -> list:
    p = Path("shipper/ship_log.jsonl")
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(errors="replace").splitlines()[-n:]:
        try:
            d = json.loads(line)
            rows.append({"status": d.get("status"), "type": d.get("type"),
                         "detail": (d.get("detail") or "")[:60],
                         "earned_usd": d.get("earned_usd", 0)})
        except json.JSONDecodeError:
            continue
    return rows


def status() -> dict:
    return {
        "enabled": JEV_ENABLED,
        "has_key": bool(os.environ.get("TYPESAFE_API_KEY", "").strip()),
        "available": available(),
        "min_confidence": MIN_CONFIDENCE,
        "yes_threshold": YES_THRESHOLD,
        "decision_log": str(DECISION_LOG),
        "decisions_recorded": (sum(1 for _ in open(DECISION_LOG))
                               if DECISION_LOG.exists() else 0),
    }
