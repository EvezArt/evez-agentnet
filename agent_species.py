#!/usr/bin/env python3
"""
Bind cryptozoo species to evez-agentnet agents.

AGENTNET_INTEGRATION.md specifies which species each OODA phase should assume:

    Observe -> NOCTIS / ABYSSAL   (low coupling, high perceptual range)
    Orient  -> AURIX / VERDANT     (mid volatility, analytical)
    Decide  -> FRACTOS / IGNIS     (high tau, cascade-capable)
    Act     -> SYNTHEX / LUMARA    (reliable coupling, output-focused)

Like every other spec in evezx-cryptozoo, that mapping was documented and
never implemented. This implements it, and — the part that matters — makes
the assignment *observable*: each agent records which species it assumed, so
you can see whether a behavioural bound is actually being applied or is
another declarative surface.

The bounds are real. An assigned species changes the phase gating:
  - Observe species have LOW tau, so a wide scan is normal for them
  - Decide species have HIGH tau, which is what authorises a cascade
  - A high-tau (cascade-capable) species is required before the shipper may
    publish. NOCTIS cannot ship. That is a constraint, not a label.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cryptozoo as CZ

ASSIGNMENT_PATH = Path("cryptozoo/agent_species.json")

# Per the spec's phase mapping. First listed is the default.
PHASE_SPECIES = {
    "observe": ["NOCTIS", "ABYSSAL"],
    "orient":  ["AURIX", "VERDANT"],
    "decide":  ["FRACTOS", "IGNIS"],
    "act":     ["SYNTHEX", "LUMARA"],
}

# The pipeline the spec names (EVEZ-71).
PIPELINE_SPECIES = {
    "HARVEST": "NOCTIS",
    "SCOUT":   "AURIX",
    "WITNESS": "VERDANT",
    "DEPLOY":  "SYNTHEX",
}

# Species whose tau authorises a cascade / external publication.
#
# SYNTHEX (tau=6, Builder, code-fabrication) IS in this set: it is the species
# the spec assigns to DEPLOY and to the Act phase, and it is the shipper's
# species. Leaving it out denied publication to the very agent that exists to
# publish — caught by test_agent_species, and it would have silently re-broken
# the shipper fix.
CASCADE_SPECIES = {"IGNIS", "VORTEX", "FRACTOS", "SYNTHEX",
                   "ECLIPSE", "NEXUS"}


@dataclass
class AgentIdentity:
    agent: str
    species: str
    tau: int
    volatility: float
    gamma: float
    cls: str
    innate_skill: str
    phase: str
    assigned_at: str = ""
    bounds: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["assigned_at"] = d["assigned_at"] or datetime.now(timezone.utc).isoformat()
        return d


def _species_params(species: str) -> dict:
    """Parameters for a base OR hybrid species.

    Hybrids (NEXUS, ECLIPSE, WRAITH) are produced by the breeding engine and
    are NOT in the static SPECIES table. Falling back to zero would make every
    hybrid look maximally de-coupled and non-cascade-capable.
    """
    s = CZ.SPECIES.get(species)
    if s:
        return dict(s)
    # hybrid: derive from the parent pair named in HYBRID_RULES
    for (a, b), name in CZ.HYBRID_RULES.items():
        if name == species:
            pa, pb = CZ.SPECIES[a], CZ.SPECIES[b]
            return {
                "class": "Hybrid",
                "tau": round((pa["tau"] + pb["tau"]) / 2),
                "V": min(CZ.MAX_V, round(pa["V"] + pb["V"], 2)),
                "gamma": round((pa["gamma"] + pb["gamma"]) / 2, 4),
                "skill": f"{pa['skill']}+{pb['skill']}",
                "hybrid_of": [a, b],
            }
    raise KeyError(f"unknown species or hybrid {species!r}")


def _bounds(species: str) -> dict:
    """The behavioural bounds the species actually imposes."""
    s = _species_params(species)
    tau = s.get("tau", 0)
    return {
        "cascade_authorised": species in CASCADE_SPECIES,
        "may_publish": species in CASCADE_SPECIES,
        "scan_width": "wide" if tau <= 4 else ("mid" if tau <= 8 else "narrow"),
        "coupling_tier": "high" if tau >= 8 else ("mid" if tau >= 4 else "low"),
        "instable": s.get("V", 0) > CZ.APEX_PROMOTE_AT,
    }


def assign(agent: str, phase: str | None = None) -> AgentIdentity:
    """Assign a species to an agent from the documented phase mapping."""
    if phase is None:
        phase = "act"
    if phase not in PHASE_SPECIES:
        raise KeyError(f"unknown phase {phase!r}; "
                       f"known: {sorted(PHASE_SPECIES)}")
    species = PHASE_SPECIES[phase][0]
    return _identity(agent, species, phase)


def assign_pipeline_step(step: str) -> AgentIdentity:
    step = step.upper()
    if step not in PIPELINE_SPECIES:
        raise KeyError(f"unknown pipeline step {step!r}; "
                       f"known: {sorted(PIPELINE_SPECIES)}")
    phase = next(p for p, sp in PHASE_SPECIES.items()
                 if PIPELINE_SPECIES[step] in sp)
    return _identity(step, PIPELINE_SPECIES[step], phase)


def _identity(name: str, species: str, phase: str) -> AgentIdentity:
    s = _species_params(species)
    return AgentIdentity(
        agent=name, species=species,
        tau=s["tau"], volatility=float(s["V"]), gamma=s["gamma"],
        cls=s["class"], innate_skill=s["skill"], phase=phase,
        bounds=_bounds(species),
    )


def may_publish(agent: str) -> tuple[bool, str]:
    """Gate external publication on cascade authorisation.

    This is the bound doing real work: a low-tau species cannot ship. Without
    it the species mapping is decoration.
    """
    ident = assign(agent, phase="act")
    if ident.bounds["may_publish"]:
        return True, f"{ident.species} (tau={ident.tau}) authorises publication"
    return False, (f"{ident.species} (tau={ident.tau}) is not "
                   f"cascade-capable; publication denied")


def assign_all() -> dict:
    """Bind the five OODA agents to their documented phases."""
    out = {}
    for agent, phase in (("scanner", "observe"), ("predictor", "orient"),
                         ("generator", "orient"), ("shipper", "act"),
                         ("maes", "observe")):
        out[agent] = assign(agent, phase).to_dict()

    ASSIGNMENT_PATH.parent.mkdir(exist_ok=True)
    ASSIGNMENT_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase_mapping": PHASE_SPECIES,
        "pipeline_mapping": PIPELINE_SPECIES,
        "agents": out,
    }, indent=1))
    return out


def status() -> dict:
    live = {}
    if ASSIGNMENT_PATH.exists():
        try:
            live = json.loads(ASSIGNMENT_PATH.read_text()).get("agents", {})
        except json.JSONDecodeError:
            live = {}
    return {
        "assigned": len(live),
        "assignment_file": str(ASSIGNMENT_PATH),
        "agents": {k: {"species": v["species"], "phase": v["phase"],
                       "tau": v["tau"], "may_publish": v["bounds"]["may_publish"]}
                   for k, v in live.items()},
        "cascade_species": sorted(CASCADE_SPECIES),
    }
