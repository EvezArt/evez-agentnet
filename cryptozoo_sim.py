#!/usr/bin/env python3
"""
CryptoZoo simulation — does the breeding engine actually produce anything
interesting, or only pass assertions?

Runs a real population: seed all 12 species, evolve the Kuramoto dynamics,
select by fitness, breed, and report what happened. Selection pressure is
applied by truncating to the top N each generation, which is the standard
approach and makes the outcome inspectable.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cryptozoo as CZ


def simulate(seeds: int = 6, generations: int = 12, keep: int = 14,
             seed: int = 20261002) -> dict:
    rng = random.Random(seed)

    pop: list[CZ.Organism] = []
    for sp in CZ.SPECIES:
        for _ in range(seeds):
            pop.append(CZ.spawn(sp))

    CZ.evolve(pop, steps=40, seed=seed)
    start = CZ.population_report(pop)
    history = [{"gen": 0, **start}]

    bred_total = 0
    refused: dict[str, int] = {}
    hybrids_seen: dict[str, int] = {}

    for g in range(1, generations + 1):
        # ── evolve the oscillators ──
        CZ.evolve(pop, steps=40, seed=seed + g)

        # ── select: fittest `keep`, with a per-species floor so the gene
        # pool stays diverse enough for named hybrids to occur ──
        before_sel = len(pop)
        pop = CZ.select_survivors(pop, keep)
        dropped = before_sel - len(pop)

        # ── breed to refill ──
        children: list[CZ.Organism] = []
        attempts = 0
        while len(children) < dropped and attempts < 200:
            attempts += 1
            a, b = rng.sample(pop, 2) if len(pop) >= 2 else (pop[0], pop[0])
            r = CZ.breed(a, b, rng=rng)
            if not r["ok"]:
                key = r["reason"].split(":")[0]
                refused[key] = refused.get(key, 0) + 1
                continue
            bred_total += 1
            if r["named_hybrid"]:
                hybrids_seen[r["named_hybrid"]] = hybrids_seen.get(r["named_hybrid"], 0) + 1
            children.append(r["child"])

        pop.extend(children)
        history.append({"gen": g, **CZ.population_report(pop)})

    return {
        "seed": seed,
        "seeds_per_species": seeds,
        "generations": generations,
        "selection": f"truncation, keep {keep}",
        "start": start,
        "end": history[-1],
        "history": history,
        "bred": bred_total,
        "refused_pairings": refused,
        "named_hybrids_produced": hybrids_seen,
        "coherence_curve": [h["coherence"] for h in history],
        "fitness_curve": [h["mean_fitness"] for h in history],
        "final_species": CZ.population_report(pop)["by_species"],
    }


def main() -> int:
    r = simulate()

    print("CRYPTOZOO SIMULATION")
    print(f"  seeds/species   : {r['seeds_per_species']}")
    print(f"  generations     : {r['generations']}")
    print(f"  selection       : {r['selection']}")
    print(f"  offspring bred : {r['bred']}")
    print()
    print(f"{'gen':>4} {'pop':>5} {'coherence':>10} {'mean_fit':>9} {'hybrids':>8}")
    for h in r["history"]:
        print(f"{h['gen']:>4} {h['size']:>5} {h['coherence']:>10} "
              f"{h['mean_fitness']:>9} {h['hybrids']:>8}")

    print()
    print("refused pairings (forbidden rules actually fired):")
    if r["refused_pairings"]:
        for k, v in sorted(r["refused_pairings"].items(), key=lambda kv: -kv[1]):
            print(f"  {v:>4}  {k}")
    else:
        print("  none — selection never sampled a forbidden pair")

    print()
    print("named hybrids produced:")
    if r["named_hybrids_produced"]:
        for k, v in sorted(r["named_hybrids_produced"].items(), key=lambda kv: -kv[1]):
            print(f"  {v:>4}  {k}")
    else:
        print("  none")

    print()
    print("final population by species:")
    for k, v in list(r["final_species"].items())[:12]:
        print(f"  {k:12} {v:>4}")

    c0, c1 = r["coherence_curve"][0], r["coherence_curve"][-1]
    f0, f1 = r["fitness_curve"][0], r["fitness_curve"][-1]
    print()
    print(f"coherence : {c0:.3f} -> {c1:.3f}")
    print(f"fitness   : {f0:.3f} -> {f1:.3f}")

    out = Path("cryptozoo/simulation.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(r, indent=1, default=str))
    print(f"\nwrote {out}")

    # A run that bred nothing or lost all coherence would be a silent failure.
    if r["bred"] == 0:
        print("\nFAIL: no offspring were produced")
        return 1
    if c1 < 0.05:
        print("\nFAIL: population decohered completely")
        return 1
    print("\nsimulation produced a viable population")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
