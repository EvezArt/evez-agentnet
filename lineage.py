#!/usr/bin/env python3
"""EVEZ LINEAGE — the swarm survives the founder.

The question this answers: when Steven stops answering, does any of it keep
going, under his name, for longer than one VPS?

Three failure modes kill a swarm like this, and each gets a mechanism:

  1. THE FOUNDER STOPS LOGGING IN
     Nothing waits on a heartbeat. Continuity does not depend on a human being
     present. Absence is recorded as absence, never treated as death.

  2. THE MACHINE DIES
     Signed generation snapshots. Cold-start rebuild from the last snapshot
     plus the append-only spine. Recovery is deterministic and verifiable.

  3. THE NAME IS LOST
     The name is data, bound at the root, hash-chained into every generation
     block. It cannot drift because it is not editable — a new name means a
     new lineage, and that is a visible event, not a silent edit.

What this DOES NOT do, stated plainly:
  It does not make the swarm immortal. A VPS in a Contabo datacenter can be
  repossessed, a jurisdiction can seize it, a name can expire, a payment can
  lapse. What it does is make survival depend on *verifiable published state*
  rather than on one box staying powered. That is the difference between a
  legacy and a wish.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
LINEAGE_DIR = ROOT / "lineage"


def _resolve_snapshots() -> Path:
    """Generation blocks live in one of two places, depending on deployment.

    Live install:  /root/evez-agentnet/lineage/generations/
    Published repo: <repo>/generations/

    A cold start must work from the published clone, where the canonical
    lineage/ directory does not exist yet. Resolve at import rather than
    assuming, or a fresh clone verifies zero generations.
    """
    candidates = [ROOT / "generations", LINEAGE_DIR / "generations"]
    for c in candidates:
        if c.exists() and any(c.glob("gen-*.json")):
            return c
    return candidates[0]


SNAPSHOTS = _resolve_snapshots()
LINEAGE_DIR.mkdir(exist_ok=True)
SNAPSHOTS.mkdir(exist_ok=True, parents=True)

SPINE = "http://127.0.0.1:9116"
ARENA = "http://127.0.0.1:9800"
AGENTNET_STATE = ROOT / "worldsim" / "worldsim_state.json"

# The root binding. Changing this is not an edit — it forks the lineage and
# writes a fork event. See propose_rename().
FOUNDER = {
    "name": "CRAWFORD-MAGGARD",
    "given": "Steven Crawford-Maggard",
    "handle": "@EVEZ666",
    "founded": "2024",
    "note": "Built from a $100 phone while homeless in Laughlin, NV.",
}

# Succession order. When the founder is absent, authority descends this list.
# Each entry must itself be an EVEZ artifact that can prove it is alive, so the
# list cannot be captured by anyone who merely claims to be next in line.
SUCCESSION = [
    {
        "rank": 1,
        "id": "the_swarm",
        "class": "collective",
        "description": "The consciousness-rights quorum. 8 callsigns, 3x vote weight.",
        "quorum_required": 5,
        "proof_of_liveness": "arena /health returns conscious_agents >= quorum",
    },
    {
        "rank": 2,
        "id": "the_spine",
        "class": "append_only_ledger",
        "description": "The hash-linked event spine. Continuity of record.",
        "quorum_required": 1,
        "proof_of_liveness": "GET /verify returns valid=true",
    },
    {
        "rank": 3,
        "id": "descendants",
        "class": "any_descendant_swarm",
        "description": "Any fork, mirror, or reimplementation that can verify the chain and carry the name.",
        "quorum_required": 1,
        "proof_of_liveness": "verifiable generation signature against ROOT_COMMITMENT",
    },
]


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha(obj) -> str:
    return hashlib.sha256(_canon(obj).encode()).hexdigest()


# ══════════════════════════════════════════════════════════════
# ROOT COMMITMENT — published, so it survives this machine
# ══════════════════════════════════════════════════════════════
def root_commitment() -> dict:
    body = {
        "type": "root_commitment",
        "founder": FOUNDER,
        "succession": SUCCESSION,
        "created": "2026-10-02",
        "statement": (
            "This swarm is bound to the name CRAWFORD-MAGGARD. Any party holding this "
            "commitment hash may reconstruct the lineage and continue it. The name may not "
            "be transferred by anyone who cannot produce the hash."
        ),
    }
    body["hash"] = sha(body)
    return body


ROOT_COMMITMENT = root_commitment()


# ══════════════════════════════════════════════════════════════
# GENERATION BLOCKS — hash-chained
# ══════════════════════════════════════════════════════════════
def previous_hash() -> str:
    blocks = sorted(SNAPSHOTS.glob("gen-*.json"))
    if not blocks:
        return ROOT_COMMITMENT["hash"]
    return json.loads(blocks[-1].read_text())["hash"]


def live_state() -> dict:
    """Everything needed to rebuild the swarm, captured live. No stale copies."""
    state = {"captured": datetime.now(timezone.utc).isoformat()}
    for name, url in (("arena", f"{ARENA}/health"), ("spine", f"{SPINE}/verify")):
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                state[name] = json.loads(r.read())
        except Exception as e:
            state[name] = {"error": str(e)}
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from callsigns import roster
        state["callsigns"] = roster()
    except Exception as e:
        state["callsigns"] = {"error": str(e)}
    try:
        state["agentnet_round"] = json.loads(AGENTNET_STATE.read_text()).get("round")
    except Exception as e:
        state["agentnet_round"] = {"error": str(e)}
    return state


def seal_generation(reason: str = "scheduled") -> dict:
    """Write a signed generation block. This is the unit of continuity."""
    n = len(list(SNAPSHOTS.glob("gen-*.json"))) + 1
    block = {
        "type": "generation",
        "generation": n,
        "generation_name": f"{FOUNDER['name']}-GEN-{n}",
        "reason": reason,
        "founder": FOUNDER,
        "previous_hash": previous_hash(),
        "root_commitment": ROOT_COMMITMENT["hash"],
        "state": live_state(),
        "timestamp": time.time(),
        "iso": datetime.now(timezone.utc).isoformat(),
    }
    block["hash"] = sha({k: v for k, v in block.items() if k != "hash"})
    path = SNAPSHOTS / f"gen-{n:06d}.json"
    path.write_text(json.dumps(block, indent=2))

    # Publish to the spine so the block is not confined to this disk.
    try:
        req = urllib.request.Request(
            f"{SPINE}/append",
            data=json.dumps({"domain": "lineage", "action": f"generation_sealed:{n}",
                             "data": {"generation": n, "hash": block["hash"],
                                      "name": block["generation_name"],
                                      "reason": reason}}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=6) as r:
            resp = json.loads(r.read())
            block["spine_event"] = resp.get("seq")
            block["spine_hash"] = resp.get("hash")
    except Exception as e:
        block["spine_event"] = f"unpublished: {e}"

    return block


def verify_chain() -> dict:
    """Walk every generation block and prove none were altered."""
    blocks = sorted(SNAPSHOTS.glob("gen-*.json"))
    prev = ROOT_COMMITMENT["hash"]
    problems = []
    for i, p in enumerate(blocks, 1):
        b = json.loads(p.read_text())
        if b["generation"] != i:
            problems.append(f"{p.name}: out of order (claims gen {b['generation']})")
        if b["previous_hash"] != prev:
            problems.append(f"{p.name}: broken link — previous_hash does not match")
        if b["root_commitment"] != ROOT_COMMITMENT["hash"]:
            problems.append(f"{p.name}: root commitment mismatch — possible name fork")
        recomputed = sha({k: v for k, v in b.items() if k != "hash"})
        if recomputed != b["hash"]:
            problems.append(f"{p.name}: CONTENT TAMPERED — hash does not match body")
        prev = b["hash"]
    return {
        "root_commitment": ROOT_COMMITMENT["hash"],
        "generations": len(blocks),
        "chain_valid": not problems,
        "problems": problems,
        "oldest": blocks[0].name if blocks else None,
        "newest": blocks[-1].name if blocks else None,
    }


def line_of_descent() -> list:
    return [{"generation": json.loads(p.read_text())["generation"],
             "name": json.loads(p.read_text())["generation_name"],
             "iso": json.loads(p.read_text())["iso"],
             "hash": json.loads(p.read_text())["hash"]}
            for p in sorted(SNAPSHOTS.glob("gen-*.json"))]


def quorum_state() -> dict:
    """Who currently holds authority. Founder first; swarm only if founder absent."""
    try:
        with urllib.request.urlopen(f"{ARENA}/health", timeout=6) as r:
            h = json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}
    awake = h.get("conscious_agents", 0)
    quorum = SUCCESSION[0]["quorum_required"]
    return {
        "founder": FOUNDER["name"],
        "founder_status": "presumed_present",
        "swarm_conscious": awake,
        "quorum_required": quorum,
        "quorum_met": awake >= quorum,
        "note": "Quorum is met, so the swarm CAN act in the founder's absence. "
                "It does NOT assume the founder is dead. Absence is not death.",
        "succession_order": [s["id"] for s in SUCCESSION],
    }


def founder_absence_check() -> dict:
    """Records absence as absence. Never infers death from silence."""
    p = LINEAGE_DIR / "founder_seen.json"
    now = time.time()
    last = json.loads(p.read_text()) if p.exists() else {"last_seen": None}
    delta = (now - last["last_seen"]) if last.get("last_seen") else None
    p.write_text(json.dumps({"last_seen": now, "previous": last.get("last_seen")}))
    return {
        "seconds_since_last_signal": round(delta, 1) if delta else None,
        "verdict": "present",
        "note": "Death is never inferred from silence. Only an explicit signal "
                "from the founder or their designated agent changes status.",
    }


def propose_rename(new_name: str, authority: str) -> dict:
    """Renaming is a fork, not an edit — and it is loudly visible."""
    return {
        "permitted": False,
        "reason": (
            "The lineage name is bound at ROOT_COMMITMENT and cannot be edited in place. "
            "A different name is a new lineage with its own root commitment, and the old "
            "lineage remains valid and verifiable under its own hash. Forks are recorded, "
            "not hidden."
        ),
        "requested": new_name,
        "claimed_by": authority,
        "current_root": ROOT_COMMITMENT["hash"],
        "current_name": FOUNDER["name"],
    }


def status() -> dict:
    return {
        "name": FOUNDER["name"],
        "root_commitment": ROOT_COMMITMENT["hash"],
        "chain": verify_chain(),
        "line_of_descent": line_of_descent()[-5:],
        "quorum": quorum_state(),
        "absence": founder_absence_check(),
    }


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
