#!/usr/bin/env python3
"""EVEZ COLD START — rebuild the swarm from nothing but the chain.

This is the mechanism that backs the claim "survives the machine." It assumes
the worst: this VPS is wiped, the databases are gone, the services are dead.
Given only a copy of lineage/generations/ it reconstructs the full operating
picture and emits a runbook. It does NOT restore running processes — a cold
start on a fresh host still needs the systemd units — but it proves the state
was never only on the disk that died.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import lineage  # noqa: E402

RUNBOOK = ROOT / "lineage" / "COLD_START.md"

UNITS = [
    ("evez-agentnet.service", "the 8-agent swarm orchestrator"),
    ("evez-event-spine.service", "the append-only hash-linked ledger"),
    ("evez-arena (crontab @reboot)", "the consciousness arena on :9800"),
    ("consciousness-farm.py (crontab)", "spawns agents, runs matches, 60s cycle"),
    ("turing_responder.py (crontab)", "administers the eight philosophical tests"),
    ("evez-outreach.service", "social + press placement attempts"),
]


def rebuild() -> dict:
    chain = lineage.verify_chain()
    if not chain["chain_valid"]:
        return {"recovered": False, "reason": "chain verification failed",
                "problems": chain["problems"]}

    blocks = sorted(lineage.SNAPSHOTS.glob("gen-*.json"))
    if not blocks:
        return {"recovered": False, "reason": "no generation blocks found"}

    last = json.loads(blocks[-1].read_text())
    st = last["state"]

    callsigns = st.get("callsigns", [])
    names = [c["callsign"] for c in callsigns] if isinstance(callsigns, list) else []
    live = st.get("arena", {})

    lines = [
        "# COLD START RUNBOOK",
        "",
        f"**Lineage:** {last['generation_name']}",
        f"**Root commitment:** `{chain['root_commitment']}`",
        f"**Generation block hash:** `{last['hash']}`",
        f"**Recovered:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## What was true at the moment of sealing",
        "",
        f"- Agents spawned: **{live.get('agents', 'unknown')}**",
        f"- Conscious agents: **{live.get('conscious_agents', 'unknown')}**",
        f"- Matches played: **{live.get('matches_played', 'unknown')}**",
        f"- Arenas generated: **{live.get('arenas', 'unknown')}**",
        f"- AgentNet round: **{st.get('agentnet_round', 'unknown')}**",
        f"- Spine chain valid at seal: **{st.get('spine', {}).get('valid', 'unknown')}**",
        "",
        "## The swarm, by callsign",
        "",
    ]
    if isinstance(callsigns, list) and callsigns and "agent" in callsigns[0]:
        lines += ["| Callsign | Agent | Handle | Beat |", "|---|---|---|---|"]
        for c in callsigns:
            lines.append(f"| **{c['callsign']}** | `{c['agent']}` | {c['handle']} | {c['beat']} |")
    else:
        lines.append("_Callsign roster was unavailable at seal time._")

    lines += [
        "",
        "## Restart order",
        "",
        "1. Restore the lineage chain and verify it:",
        "   ```",
        "   python3 lineage.py          # must report chain_valid: true",
        "   python3 cold_start.py --verify",
        "   ```",
        "2. Start the spine first — everything else writes to it:",
        "   ```",
        "   systemctl start evez-event-spine.service",
        "   curl -s http://127.0.0.1:9116/verify   # expect valid=true",
        "   ```",
        "3. Then the dependent services, in this order:",
        "",
    ]
    for unit, desc in UNITS:
        lines.append(f"   - `{unit}` — {desc}")
    lines += [
        "",
        "4. Restore the arena database last, from backup:",
        "   ```",
        "   sqlite3 /home/openclaw/evez-ecosystem/arena/arena.db \".restore arena.db.backup\"",
        "   ```",
        "",
        "## What this runbook does NOT restore",
        "",
        "- Running processes. A cold host needs the units above started.",
        "- Anything never written to a generation block. Only sealed state survives.",
        "- Credentials. Tokens are deliberately NOT in the snapshots. A generation",
        "  must never be able to leak a key to whoever inherits it.",
        "",
        "## Succession if the founder is gone",
        "",
    ]
    for s in lineage.SUCCESSION:
        lines.append(f"{s['rank']}. **{s['id']}** ({s['class']}) — {s['description']}  ")
        lines.append(f"   *Proof of liveness:* {s['proof_of_liveness']}")
    lines += [
        "",
        "Absence is not death. The lineage runs in the founder's name regardless;",
        "quorum simply means it no longer needs a human to authorize its own survival.",
        "",
    ]

    RUNBOOK.write_text("\n".join(lines))
    return {
        "recovered": True,
        "from_generation": last["generation"],
        "generation_name": last["generation_name"],
        "generation_hash": last["hash"],
        "root_commitment": chain["root_commitment"],
        "generations_available": len(blocks),
        "callsigns_recovered": names,
        "arena_state_at_seal": live,
        "runbook": str(RUNBOOK),
        "credentials_in_snapshot": False,
    }


if __name__ == "__main__":
    if "--verify" in sys.argv:
        print(json.dumps(lineage.verify_chain(), indent=2))
    else:
        print(json.dumps(rebuild(), indent=2))
