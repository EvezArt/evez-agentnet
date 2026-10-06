#!/usr/bin/env python3
"""
JEV integration for the evez-agentnet OODA loop.

This is what "use Jev" means concretely: Jev runs inside the loop, every
round, and its judgements are recorded against real state.

Design rule — Jev ADVISES, it does not OVERRIDE. The deterministic pipeline
decides; Jev's probability sits alongside it in the log and the spine. Two
reasons:

  1. Correctness. A single probabilistic call must not be able to halt the
     scan/predict/generate/ship pipeline. The loop has to keep running.
  2. Honesty. If Jev's advice overrode behaviour, the loop would be making
     decisions with a fabricated signal whenever the key is missing. Instead
     the log says exactly which tier produced each outcome.

Agreement between the deterministic rule and Jev is itself a signal worth
recording: when they disagree, that is a lead worth investigating, not a
silent override.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import jev_decisions as JD

log = logging.getLogger("agentnet.jev_integration")

SPINE_PATH = "spine/spine.jsonl"


def _append_spine(event: str, data: dict, *, jev_decision_hash: str = None) -> None:
    """Append via the orchestrator's own chainer so Jev entries are
    hash-linked like everything else. Falls back to a plain write if the
    orchestrator is not importable (standalone use).
    
    If jev_decision_hash is provided, it is embedded in the spine entry,
    creating an attribution chain from the Jev decision to the spine.
    """
    try:
        from orchestrator import append_spine
        append_spine(event, data)
    except Exception:
        try:
            import hashlib
            from pathlib import Path
            from datetime import datetime, timezone
            p = Path(SPINE_PATH)
            p.parent.mkdir(exist_ok=True)
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event,
                "data": data,
            }
            if jev_decision_hash:
                entry["jev_decision_hash"] = jev_decision_hash
            entry["sha256"] = hashlib.sha256(
                json.dumps(entry, sort_keys=True).encode()).hexdigest()[:16]
            with open(p, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


def advise(state: dict, round_no: int) -> dict:
    """Run every JEV judgement for this round. Never raises."""
    out = {
        "round": round_no,
        "ts": datetime.now(timezone.utc).isoformat(),
        "available": JD.available(),
        "judgements": {},
        "agreement": {},
    }

    if not JD.available():
        out["tier"] = "deterministic-only"
        out["note"] = ("Jev not configured — every judgement returns an "
                       "explicit fallback. The pipeline is unaffected.")
        _append_spine("jev_advice", out)
        return out

    out["tier"] = "jev+deterministic"

    # ── 1. which agent needs attention? ──
    att = JD.judge_attention_target(state)
    out["judgements"]["attention_target"] = _slim(att)

    # ── 2. is the shipper broken or merely unconfigured? ──
    ship = JD.judge_shipper_health(state)
    out["judgements"]["shipper_health"] = _slim(ship)

    # ── 3. should a human be paged? ──
    brief = ""
    try:
        from pathlib import Path
        b = Path("status/BRIEF.md")
        if b.exists():
            brief = b.read_text(errors="replace")
    except Exception:
        pass
    health = {}
    try:
        from pathlib import Path
        h = Path("status/HEALTH.json")
        if h.exists():
            health = json.loads(h.read_text())
    except Exception:
        pass
    esc = JD.judge_escalation(brief, health)
    out["judgements"]["escalation"] = _slim(esc)

    # ── 4. cross-check against the deterministic RSI output ──
    hyps = (state.get("rsi") or {}).get("hypotheses") or []
    det_target = _deterministic_target(state)
    jev_target = out["judgements"]["attention_target"].get("target", {}).get("choice")
    out["agreement"] = {
        "deterministic_lowest_rep_agent": det_target,
        "jev_choice": jev_target,
        "agree": (det_target == jev_target) if jev_target else None,
        "rsi_hypotheses_this_round": [h.get("action") for h in hyps][:3],
    }
    if jev_target and det_target and jev_target != det_target:
        log.info("[JEV] disagrees with min(reputation): det=%s jev=%s",
                 det_target, jev_target)

    _append_spine("jev_advice", out)
    return out


def _slim(r: dict) -> dict:
    """Drop the bulky raw payload; keep the decision and its provenance."""
    keep = {k: v for k, v in r.items() if k != "raw"}
    return keep


def _deterministic_target(state: dict) -> str | None:
    agents = state.get("agents") or {}
    if not agents:
        return None
    return min(agents, key=lambda a: agents[a].get("reputation", 1.0))


def summarise(advice: dict) -> str:
    """One-line-per-judgement summary for the orchestrator log."""
    if not advice.get("available"):
        return "Jev not configured — deterministic tier only"
    parts = []
    for name, j in advice.get("judgements", {}).items():
        bits = []
        tgt = j.get("target")
        if isinstance(tgt, dict):
            bits.append(f"choice={tgt.get('choice')} conf={tgt.get('confidence')}"
                        + (" ABSTAINED" if tgt.get("abstained") else ""))
        brk = j.get("broken")
        if isinstance(brk, dict):
            bits.append(f"P(broken)={brk.get('probability')} -> {brk.get('verdict')}")
        sev = j.get("severity")
        if isinstance(sev, dict):
            bits.append(f"severity={sev.get('score')}")
        esc = j.get("escalate")
        if isinstance(esc, dict):
            bits.append(f"P(escalate)={esc.get('probability')} -> {esc.get('verdict')}")
        if bits:
            parts.append(f"{name}[{', '.join(bits)}]")
    ag = advice.get("agreement") or {}
    if ag.get("agree") is not None:
        parts.append(f"agreement_with_min_rep={ag['agree']}")
    return " | ".join(parts) or "no judgements"
