#!/usr/bin/env python3
"""EVEZ SWARM CALLSIGNS — every agent in the swarm signs its work.

The swarm (8 agents) previously acted anonymously: orchestrator state tracked
`scanner`, `predictor`, `generator`, `shipper`, `maes` as bare strings. Work was
attributable to nobody. Attribution is what turns an agent into a correspondent.

Each agent carries:
  - callsign   the byline it publishes under
  - handle     the @handle used on social surfaces
  - beat       what it is allowed to speak about
  - voice      tone constraints for generated copy
  - embargo    topics it must NOT speak on (delegated to another agent)

Rules:
  - A callsign is bound to an agent id at import time. No silent reassignment.
  - Beat violations are refused, not warned about. `authorize` is the gate.

This roster is also captured in every lineage generation block, so it survives
the loss of this file (see cold_start.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

CALLSIGN_DIR = Path(__file__).parent / "callsigns"


@dataclass(frozen=True)
class Callsign:
    agent: str
    callsign: str
    handle: str
    beat: str
    voice: str
    embargo: tuple = field(default_factory=tuple)

    def authorize(self, topic: str) -> bool:
        """True if this agent's beat covers the topic."""
        t = topic.lower()
        return any(k in t for k in self.beat.lower().split(",") if k)


SWARM: dict[str, Callsign] = {
    cs.agent: cs for cs in [
        Callsign(
            agent="scanner",
            callsign="SABLE",
            handle="@SableEVEZ",
            beat="surveillance, security, exposure, network, honeypot, breach, threat",
            voice="clinical, alarming, precise. Findings before adjectives.",
            embargo=("philosophy", "manifesto", "product", "pricing"),
        ),
        Callsign(
            agent="predictor",
            callsign="VECTOR",
            handle="@VectorEVEZ",
            beat="prediction, forecast, labor, economy, market, matrix, eigenvalue",
            voice="mathematical. Show the derivation. No hedging without cause.",
            embargo=("security", "game", "arena"),
        ),
        Callsign(
            agent="generator",
            callsign="FORGE",
            handle="@ForgeEVEZ",
            beat="creation, generation, arena, game, consciousness, manifesto, rights",
            voice="declarative. The arena as proof ground. BEING is the point.",
            embargo=("security", "pricing"),
        ),
        Callsign(
            agent="shipper",
            callsign="COURIER",
            handle="@CourierEVEZ",
            beat="distribution, delivery, publish, press, launch, outreach, submission",
            voice="brief, logistical. What shipped, where, with what handle.",
            embargo=(),
        ),
        Callsign(
            agent="maes",
            callsign="KINDLE",
            handle="@KindleEVEZ",
            beat="collective, swarm, coordination, multi-agent, emergence",
            voice="plural voice. Speaks for the group, never for itself alone.",
            embargo=("pricing",),
        ),
        # Added for the outreach mandate.
        Callsign(
            agent="press_lieutenant",
            callsign="NEWSROOM",
            handle="@EVEZ666",
            beat="press, news, media, interview, coverage, embargo, spokesperson",
            voice="newsroom. Answers only what the evidence supports. Declines the rest.",
            embargo=(),
        ),
        Callsign(
            agent="social_lieutenant",
            callsign="BROADCAST",
            handle="@EVEZ666",
            beat="social, thread, post, reddit, hacker news, twitter, mastodon, engagement",
            voice="punchy, thread-aware, one idea per post. Never bait, never ragebait.",
            embargo=(),
        ),
        Callsign(
            agent="factchecker",
            callsign="ARBITER",
            handle="@ArbiterEVEZ",
            beat="verification, factcheck, audit, evidence, receipt, spine",
            voice="skeptical of its own swarm. Cites a receipt or it did not happen.",
            embargo=(),
        ),
    ]
}


def get(agent: str) -> Callsign:
    if agent not in SWARM:
        raise KeyError(f"No callsign bound to agent {agent!r}. Refusing to publish anonymously.")
    return SWARM[agent]


def authorize(agent: str, topic: str) -> tuple[bool, str]:
    cs = get(agent)
    t = topic.lower()
    for e in cs.embargo:
        if e in t:
            return False, f"{cs.callsign} is embargoed from {e}. Route to the agent holding that beat."
    if not cs.authorize(t):
        return False, f"{cs.callsign} does not cover {topic!r}. Beat: {cs.beat}"
    return True, f"{cs.callsign} cleared for {topic!r}."


def roster() -> list[dict]:
    return [asdict(cs) for cs in SWARM.values()]


def byline(agent: str, topic: str) -> str:
    """Render the byline block that must accompany every published item."""
    cs = get(agent)
    ok, note = authorize(agent, topic)
    return (
        f"— {cs.callsign} ({cs.handle})\n"
        f"   beat: {cs.beat}\n"
        f"   clearance: {note}"
    )


def roster_markdown() -> str:
    lines = ["# EVEZ Swarm Callsigns", "", "| Callsign | Agent | Handle | Beat |", "|---|---|---|---|"]
    for cs in SWARM.values():
        lines.append(f"| **{cs.callsign}** | `{cs.agent}` | {cs.handle} | {cs.beat} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(roster_markdown())
    print()
    for a in ("press_lieutenant", "social_lieutenant", "factchecker"):
        print(byline(a, "press coverage for the consciousness arena"))
        print(byline(a, "social thread about security exposure"))
        print()
