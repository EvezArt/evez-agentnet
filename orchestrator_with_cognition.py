#!/usr/bin/env python3
"""Cognition-wrapped orchestrator for evez-agentnet.

This keeps the existing orchestrator module intact and layers the restartable
LivingLogicDaemon around its pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import orchestrator as base
from cognition.checkpoint import CheckpointStore
from cognition.daemon import LivingLogicDaemon

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agentnet-cognition")


def summarize_scan(scan_results: list, maes_obs: dict, round_no: int) -> str:
    top = scan_results[:3]
    payload = {
        "round": round_no,
        "signal_count": len(scan_results),
        "maes_agents": maes_obs.get("agent_count", 0),
        "maes_players": maes_obs.get("player_count", 0),
        "top_signals": top,
    }
    return json.dumps(payload, ensure_ascii=False)


def main() -> None:
    state = base.load_state()
    state["round"] += 1
    rnd = state["round"]
    log.info("=== cognition round %s ===", rnd)
    base.append_spine("round_start", {"round": rnd, "mode": "cognition"})

    store = CheckpointStore(os.environ.get("COGNITION_STATE_DIR", ".state"))
    daemon = LivingLogicDaemon(store)

    maes_obs = base.run_maes_tick(state)
    scan_results = base.run_scan(state)
    daemon_state = daemon.step(summarize_scan(scan_results, maes_obs, rnd))

    base.append_spine(
        "cognition_step",
        {
            "round": rnd,
            "active_identity": daemon_state["active_identity"],
            "action_mode": daemon_state["action_mode"],
            "checkpoint": daemon_state["checkpoint"],
            "lineage_hash": daemon_state["lineage_hash"],
            "unresolved_count": daemon_state["revision"].get("unresolved_count", 0),
            "dark_pressure_count": daemon_state["revision"].get("dark_pressure_count", 0),
        },
    )

    action_mode = daemon_state["action_mode"]
    predictions = base.run_predict(scan_results, state)

    if action_mode == "evidence_seek":
        drafts = []
        earned = 0.0
        base.append_spine("cognition_gate", {"round": rnd, "gate": "ship_blocked_for_evidence_seek"})
    else:
        drafts = base.run_generate(predictions, state)
        if action_mode == "watch":
            earned = 0.0
            base.append_spine("cognition_gate", {"round": rnd, "gate": "ship_blocked_for_watch_mode"})
        else:
            earned = base.run_ship(drafts, state)

    state["total_earned_usd"] += earned
    base.run_openclaw(state)
    hypotheses = base.generate_rsi_hypotheses(state)
    state["rsi"]["hypotheses"] = hypotheses

    rep_summary = {k: {"rep": round(v["reputation"], 3), "streak": v.get("streak", 0)} for k, v in state["agents"].items()}
    base.append_spine(
        "round_end",
        {
            "round": rnd,
            "mode": "cognition",
            "earned_usd": earned,
            "total_earned_usd": state["total_earned_usd"],
            "agent_reputations": rep_summary,
            "active_identity": daemon_state["active_identity"],
            "action_mode": action_mode,
            "rsi_hypotheses": hypotheses,
        },
    )
    base.save_state(state)
    log.info("Round %s complete. identity=%s mode=%s", rnd, daemon_state["active_identity"], action_mode)


if __name__ == "__main__":
    while True:
        main()
        interval = int(os.environ.get("ROUND_INTERVAL", "1800"))
        log.info("Sleeping %ss until next cognition round...", interval)
        time.sleep(interval)
