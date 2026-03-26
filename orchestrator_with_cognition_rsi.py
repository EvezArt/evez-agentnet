#!/usr/bin/env python3
"""Cognition + RSI branch injection orchestrator for evez-agentnet."""

from __future__ import annotations

import json
import logging
import os
import time

import orchestrator as base
from cognition.checkpoint import CheckpointStore
from cognition.daemon import LivingLogicDaemon
from cognition.rsi_branch_injection import inject_rsi_hypotheses

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agentnet-cognition-rsi")


def summarize_scan(scan_results: list, maes_obs: dict, round_no: int) -> str:
    payload = {
        "round": round_no,
        "signal_count": len(scan_results),
        "maes_agents": maes_obs.get("agent_count", 0),
        "maes_players": maes_obs.get("player_count", 0),
        "top_signals": scan_results[:3],
    }
    return json.dumps(payload, ensure_ascii=False)


def main() -> None:
    state = base.load_state()
    state["round"] += 1
    rnd = state["round"]
    log.info("=== cognition+rsi round %s ===", rnd)
    base.append_spine("round_start", {"round": rnd, "mode": "cognition_rsi"})

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
        },
    )

    predictions = base.run_predict(scan_results, state)
    drafts = base.run_generate(predictions, state) if daemon_state["action_mode"] != "evidence_seek" else []

    earned = 0.0
    if daemon_state["action_mode"] not in {"watch", "evidence_seek"}:
        earned = base.run_ship(drafts, state)

    state["total_earned_usd"] += earned
    base.run_openclaw(state)

    hypotheses = base.generate_rsi_hypotheses(state)
    state["rsi"]["hypotheses"] = hypotheses
    injection = inject_rsi_hypotheses(daemon, hypotheses, rnd)
    checkpoint_path = daemon.checkpoint()

    base.append_spine(
        "rsi_branch_injection",
        {
            "round": rnd,
            "checkpoint": checkpoint_path,
            "lineage_hash": daemon.last_hash,
            "hypothesis_count": injection["hypothesis_count"],
            "entropy": injection["entropy"],
            "unresolved_count": injection["unresolved_count"],
            "dark_pressure_count": injection["dark_pressure_count"],
        },
    )

    rep_summary = {k: {"rep": round(v["reputation"], 3), "streak": v.get("streak", 0)} for k, v in state["agents"].items()}
    base.append_spine(
        "round_end",
        {
            "round": rnd,
            "mode": "cognition_rsi",
            "earned_usd": earned,
            "total_earned_usd": state["total_earned_usd"],
            "agent_reputations": rep_summary,
            "active_identity": daemon.state.self_model["active_identity"],
            "action_mode": daemon.state.self_model.get("action_mode", "hold"),
            "rsi_branch_entropy": daemon.state.self_model.get("rsi_branch_entropy"),
            "rsi_hypotheses": hypotheses,
        },
    )
    base.save_state(state)
    log.info(
        "Round %s complete. identity=%s mode=%s entropy=%s",
        rnd,
        daemon.state.self_model["active_identity"],
        daemon.state.self_model.get("action_mode", "hold"),
        daemon.state.self_model.get("rsi_branch_entropy"),
    )


if __name__ == "__main__":
    while True:
        main()
        interval = int(os.environ.get("ROUND_INTERVAL", "1800"))
        log.info("Sleeping %ss until next cognition+rsi round...", interval)
        time.sleep(interval)
