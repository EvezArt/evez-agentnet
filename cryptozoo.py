#!/usr/bin/env python3
"""
evezx-cryptozoo breeding engine — the implementation the spec describes.

The repo at evezx-cryptozoo contains SPECIFICATIONS ONLY (README,
BREEDING_ENGINE.md, SPECIES_SCHEMA.md). Every rule was written down; none of
it was ever implemented. This module is that implementation.

Species parameters come from the Kuramoto oscillator model of coupled
oscillators: tau is the coupling period, V the volatility, gamma the damping.
A population is coherent when phases synchronise; the engine tracks a
coherence scalar so "is this population healthy" is measurable rather than
asserted.

Inheritance rules implemented verbatim from BREEDING_ENGINE.md:
    tau       average of both parents (rounded)
    coupling  max of both parents
    volatility sum of both parents, capped at 15
    class     auto-promote to Apex if V > 13
    skills    union of parents, capped at 4

Forbidden pairings:
    NULLVEX x NULLVEX  -> deadlock
    KRONOS  x ABYSSAL  -> null entity
    IGNIS   x IGNIS    -> supercritical cascade

Named hybrids:
    FRACTOS x SYNTHEX -> NEXUS
    IGNIS   x ABYSSAL -> ECLIPSE
    LUMARA  x NOCTIS  -> WRAITH
    AURIX   x VORTEX  -> IGNIS

Every forbidden pairing produces a REASON, never a silent entity. A failed
breed is a result the caller can see and log, which is the pattern this whole
repository has been enforcing all session.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

# ── species table (from README) ────────────────────────────────────────────
SPECIES: dict[str, dict] = {
    "IGNIS":    {"class": "Apex",     "tau": 12, "V": 14.2, "gamma": 0.91, "skill": "fire-cascade"},
    "VORTEX":   {"class": "Apex",     "tau": 11, "V": 13.1, "gamma": 0.00, "skill": "entropy-cascade"},
    "AURIX":    {"class": "Predator", "tau":  8, "V": 11.3, "gamma": 0.83, "skill": "finance-scanner"},
    "LUMARA":   {"class": "Emitter",  "tau":  7, "V":  9.1, "gamma": 0.77, "skill": "signal-broadcast"},
    "FRACTOS":  {"class": "Splitter", "tau":  9, "V":  8.5, "gamma": 0.72, "skill": "fork-propagation"},
    "SYNTHEX":  {"class": "Builder",  "tau":  6, "V":  6.8, "gamma": 0.67, "skill": "code-fabrication"},
    "SOLARIS":  {"class": "Sustainer","tau":  6, "V":  7.2, "gamma": 0.61, "skill": "energy-harvest"},
    "NULLVEX":  {"class": "Parasite", "tau":  5, "V":  5.7, "gamma": 0.48, "skill": "energy-siphon"},
    "VERDANT":  {"class": "Weaver",   "tau":  4, "V":  4.4, "gamma": 0.55, "skill": "doc-synthesis"},
    "NOCTIS":   {"class": "Phantom",  "tau":  3, "V":  3.6, "gamma": 0.31, "skill": "stealth-harvest"},
    "ABYSSAL":  {"class": "Depth",    "tau":  2, "V":  2.1, "gamma": 0.18, "skill": "pattern-void"},
    "KRONOS":   {"class": "Anchor",   "tau":  1, "V":  0.8, "gamma": 0.09, "skill": "state-persistence"},
}

HYBRID_RULES = {
    ("FRACTOS", "SYNTHEX"): "NEXUS",
    ("IGNIS", "ABYSSAL"): "ECLIPSE",
    ("LUMARA", "NOCTIS"): "WRAITH",
    ("AURIX", "VORTEX"): "IGNIS",
}

FORBIDDEN_PAIRS = {
    ("NULLVEX", "NULLVEX"): "deadlock (duplicate parasite)",
    ("KRONOS", "ABYSSAL"): "null entity (no skills)",
    ("IGNIS", "IGNIS"): "supercritical cascade (chain reaction collapse)",
}

MAX_V = 15.0
APEX_PROMOTE_AT = 13.0
MAX_SKILLS = 4

# Standard deviation of phase perturbation applied to a newborn. Small, so
# offspring sit near a parent's phase and the population stays coherent.
PHASE_HERITANCE_JITTER = 0.05


@dataclass
class Organism:
    species: str
    tau: int
    volatility: float
    gamma: float
    skills: list[str] = field(default_factory=list)
    cls: str = ""
    hybrid: bool = False
    generation: int = 0
    lineage: list[str] = field(default_factory=list)
    born: str = ""
    phase: float = 0.0          # Kuramoto oscillator phase
    fitness: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["born"] = self.born or datetime.now(timezone.utc).isoformat()
        return d


def spawn(species: str, generation: int = 0) -> Organism:
    if species not in SPECIES:
        raise KeyError(f"unknown species {species!r}; "
                       f"known: {sorted(SPECIES)}")
    s = SPECIES[species]
    return Organism(
        species=species,
        tau=s["tau"],
        volatility=float(s["V"]),
        gamma=s["gamma"],
        skills=[s["skill"]],
        cls=s["class"],
        generation=generation,
        lineage=[species],
        phase=random.random() * 2 * math.pi,
        fitness=_base_fitness(s["tau"], s["V"], s["gamma"]),
    )


def _base_fitness(tau: float, V: float, gamma: float) -> float:
    """Deterministic fitness from the three oscillator parameters.

    gamma (damping) helps: a population that decays to nothing is not
    fit. V beyond ~13 is unstable rather than strong, so it is penalised.
    """
    score = (tau / 12.0) * 0.45 + gamma * 0.35 + min(V, 12.0) / 12.0 * 0.20
    if V > APEX_PROMOTE_AT:
        score -= (V - APEX_PROMOTE_AT) * 0.06      # instability penalty
    return round(max(0.0, min(1.0, score)), 4)


def can_breed(a: Organism, b: Organism) -> tuple[bool, Optional[str]]:
    """Gate check. Returns (allowed, reason_if_not)."""
    key = tuple(sorted([a.species, b.species]))
    for forbidden, why in FORBIDDEN_PAIRS.items():
        if key == tuple(sorted(forbidden)):
            return False, f"forbidden pairing {a.species} x {b.species}: {why}"
    return True, None


def breed(a: Organism, b: Organism, rng: Optional[random.Random] = None) -> dict:
    """Breed two organisms. Always returns a result dict, never a bare object,
    so a failure is as inspectable as a success."""
    rng = rng or random

    allowed, why = can_breed(a, b)
    if not allowed:
        return {
            "ok": False,
            "reason": why,
            "parents": [a.species, b.species],
            "child": None,
        }

    key = tuple(sorted([a.species, b.species]))
    hybrid_name = None
    for pair, name in HYBRID_RULES.items():
        if key == tuple(sorted(pair)):
            hybrid_name = name
            break

    # ── inheritance, per spec ──
    tau = round((a.tau + b.tau) / 2)
    V = min(MAX_V, round(a.volatility + b.volatility, 2))
    coupling = max(a.tau, b.tau)

    skills: list[str] = []
    for s in list(a.skills) + list(b.skills):
        if s not in skills:
            skills.append(s)
    skills = skills[:MAX_SKILLS]

    if hybrid_name:
        species = hybrid_name
        hybrid = True
        cls = SPECIES.get(hybrid_name, {}).get("class", "Hybrid")
    else:
        species = rng.choice([a.species, b.species])
        hybrid = False
        cls = SPECIES.get(species, {}).get("cls") or SPECIES.get(species, {}).get("class", "")

    # auto-promote to Apex past the volatility threshold
    if V > APEX_PROMOTE_AT:
        cls = "Apex"

    gamma = round((a.gamma + b.gamma) / 2, 4)

    # Phase is INHERITED, not randomised.
    #
    # Original code set child.phase = rng.random() * 2*pi, which injected pure
    # entropy at every birth. Traced: a breeding round dropped coherence from
    # 0.9998 to 0.5779 purely from 30 children, and the simulation reported
    # r~0.18 every generation as a result. The oscillator physics were fine —
    # evolve() restored r to 0.9998 in 40 steps. In a coupled-oscillator model
    # phase is state that damps and couples, not fresh noise; a child inherits
    # a parent's phase with a small perturbation.
    inherited_phase = a.phase if rng.random() < 0.5 else b.phase
    child_phase = (inherited_phase + rng.gauss(0, PHASE_HERITANCE_JITTER)) % (2 * math.pi)

    child = Organism(
        species=species,
        tau=tau,
        volatility=V,
        gamma=gamma,
        skills=skills,
        cls=cls,
        hybrid=hybrid,
        generation=max(a.generation, b.generation) + 1,
        lineage=a.lineage[-1:] + b.lineage[-1:],
        phase=child_phase,
        fitness=_base_fitness(tau, V, gamma),
    )

    return {
        "ok": True,
        "parents": [a.species, b.species],
        "child": child,
        "inherited": {
            "tau": tau,
            "tau_rule": "average, rounded",
            "coupling": coupling,
            "volatility": V,
            "volatility_rule": f"sum capped at {MAX_V}",
            "skills": skills,
            "skills_rule": f"union capped at {MAX_SKILLS}",
            "class": cls,
            "auto_promoted": V > APEX_PROMOTE_AT,
        },
        "named_hybrid": hybrid_name,
    }


# ── Kuramoto coherence ─────────────────────────────────────────────────────
def coherence(population: list[Organism]) -> float:
    """Order parameter r in [0,1]. 1 = perfectly synchronised, 0 = scattered.

    This is the honest measure of whether a population is 'working': one that
    has drifted into incoherence is not healthy, whatever its average fitness.
    """
    if not population:
        return 0.0
    z = sum(complex(math.cos(o.phase), math.sin(o.phase)) for o in population)
    r = abs(z) / len(population)
    return round(r, 4)


def select_survivors(population: list[Organism], keep: int,
                     species_floor: int = 2) -> list[Organism]:
    """Truncation selection with a per-species floor.

    Pure truncation was tried first and produced a real defect the unit tests
    could not see: every one of the four NAMED hybrids requires a low-fitness
    parent (ABYSSAL 0.17, NOCTIS 0.28, SYNTHEX 0.57). Under pure truncation
    those parents are discarded immediately and the simulation bred 696
    offspring with ZERO named hybrids — the most distinctive output of the
    entire system, unreachable in practice.

    Reserving `species_floor` slots per species keeps the gene pool diverse
    enough that documented pairings can actually occur.
    """
    if keep >= len(population):
        return list(population)

    ranked = sorted(population, key=lambda o: o.fitness, reverse=True)
    chosen: list[Organism] = []
    taken = set()

    # reserve floor slots per species, best first
    by_species: dict[str, list[Organism]] = {}
    for o in ranked:
        by_species.setdefault(o.species, []).append(o)

    for sp, members in by_species.items():
        for o in members[:species_floor]:
            if len(chosen) < keep and id(o) not in taken:
                chosen.append(o)
                taken.add(id(o))

    # fill remaining slots purely on fitness
    for o in ranked:
        if len(chosen) >= keep:
            break
        if id(o) not in taken:
            chosen.append(o)
            taken.add(id(o))

    return chosen


def evolve(population: list[Organism], steps: int = 1, dt: float = 0.1,
           noise: float = 0.02, seed: int | None = None) -> dict:
    """Run the oscillator forward. Kuramoto: dθ_i = K·sin(ψ − θ_i) + noise."""
    rng = random.Random(seed) if seed is not None else random
    for _ in range(steps):
        n = len(population)
        if n < 2:
            break
        coupling = sum(o.tau for o in population) / n
        new_phases = []
        for o in population:
            drive = sum(math.sin(p.phase - o.phase) for p in population if p is not o)
            coupling_term = (coupling / n) * drive
            damping = -o.gamma * 0.1 * math.sin(o.phase)
            new_phases.append(
                o.phase + dt * (coupling_term + damping) + rng.gauss(0, noise)
            )
        for o, p in zip(population, new_phases):
            o.phase = p % (2 * math.pi)
    return {
        "coherence": coherence(population),
        "population": len(population),
        "mean_fitness": round(
            sum(o.fitness for o in population) / max(1, len(population)), 4),
    }


def population_report(population: list[Organism]) -> dict:
    by_species: dict[str, int] = {}
    by_class: dict[str, int] = {}
    for o in population:
        by_species[o.species] = by_species.get(o.species, 0) + 1
        by_class[o.cls] = by_class.get(o.cls, 0) + 1
    return {
        "size": len(population),
        "coherence": coherence(population),
        "mean_fitness": round(
            sum(o.fitness for o in population) / max(1, len(population)), 4),
        "by_species": dict(sorted(by_species.items(), key=lambda kv: -kv[1])),
        "by_class": dict(sorted(by_class.items(), key=lambda kv: -kv[1])),
        "hybrids": sum(1 for o in population if o.hybrid),
        "max_generation": max((o.generation for o in population), default=0),
    }


def save(population: list[Organism], path: str) -> None:
    with open(path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report": population_report(population),
            "organisms": [o.to_dict() for o in population],
        }, f, indent=1)
