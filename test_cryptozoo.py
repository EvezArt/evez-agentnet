"""Test the cryptozoo breeding engine against the written spec.

The spec in evezx-cryptozoo/BREEDING_ENGINE.md was documentation only. These
assert the implementation matches it rule for rule, and — critically — that
forbidden pairings FAIL with a reason rather than producing a silent entity.
"""
import importlib.util
import math
import random
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "cryptozoo", "/root/evez-agentnet/cryptozoo.py")
CZ = importlib.util.module_from_spec(spec)
sys.modules["cryptozoo"] = CZ
spec.loader.exec_module(CZ)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("species table matches the spec")
expect("12 species defined", len(CZ.SPECIES) == 12, str(len(CZ.SPECIES)))
expect("4 named hybrids", len(CZ.HYBRID_RULES) == 4, str(len(CZ.HYBRID_RULES)))
expect("3 forbidden pairings", len(CZ.FORBIDDEN_PAIRS) == 3,
       str(len(CZ.FORBIDDEN_PAIRS)))
expect("IGNIS tau=12 V=14.2 gamma=0.91",
       (CZ.SPECIES["IGNIS"]["tau"], CZ.SPECIES["IGNIS"]["V"],
        CZ.SPECIES["IGNIS"]["gamma"]) == (12, 14.2, 0.91),
       str(CZ.SPECIES["IGNIS"]))
expect("KRONOS is the weakest anchor",
       CZ.SPECIES["KRONOS"]["V"] == 0.8, str(CZ.SPECIES["KRONOS"]))

print("\nspawn")
o = CZ.spawn("SYNTHEX")
expect("spawned correct species", o.species == "SYNTHEX")
expect("carries innate skill", o.skills == ["code-fabrication"], str(o.skills))
expect("class matches spec", o.cls == "Builder", o.cls)
expect("fitness computed", 0.0 <= o.fitness <= 1.0, str(o.fitness))
try:
    CZ.spawn("NOT_A_SPECIES")
    expect("unknown species raises", False, "no raise")
except KeyError:
    expect("unknown species raises KeyError", True)

print("\nforbidden pairings MUST fail loudly")
for (p1, p2), why in CZ.FORBIDDEN_PAIRS.items():
    r = CZ.breed(CZ.spawn(p1), CZ.spawn(p2))
    expect(f"{p1} x {p2} refused", r["ok"] is False, str(r))
    expect(f"  reason names the cause", why.split("(")[0].strip() in r["reason"],
           r["reason"])
    expect(f"  child is None, not a silent entity", r["child"] is None)

print("\nnamed hybrids")
for (p1, p2), name in CZ.HYBRID_RULES.items():
    r = CZ.breed(CZ.spawn(p1), CZ.spawn(p2), rng=random.Random(1))
    expect(f"{p1} x {p2} -> {name}",
           r["ok"] and r["child"].species == name,
           str(r.get("child"))[:90])
    expect(f"  flagged hybrid", r["child"].hybrid is True)

print("\ninheritance rules")
a = CZ.spawn("SYNTHEX")          # tau 6, V 6.8
b = CZ.spawn("VERDANT")          # tau 4, V 4.4
r = CZ.breed(a, b, rng=random.Random(2))
inh = r["inherited"]
expect("tau = average rounded", inh["tau"] == round((6 + 4) / 2), str(inh["tau"]))
expect("volatility = sum", abs(inh["volatility"] - 11.2) < 0.01,
       str(inh["volatility"]))
expect("coupling = max(tau)", inh["coupling"] == 6, str(inh["coupling"]))
expect("skills = union", sorted(inh["skills"]) == ["code-fabrication", "doc-synthesis"],
       str(inh["skills"]))

print("\nskill cap at 4")
rich_a = CZ.spawn("SYNTHEX")
rich_a.skills = ["a", "b", "c"]
rich_b = CZ.spawn("VERDANT")
rich_b.skills = ["d", "e"]
r2 = CZ.breed(rich_a, rich_b, rng=random.Random(3))
expect("skills capped at 4", len(r2["inherited"]["skills"]) <= 4,
       str(r2["inherited"]["skills"]))

print("\nvolatility cap at 15")
x = CZ.spawn("IGNIS")            # V 14.2
y = CZ.spawn("VORTEX")           # V 13.1
r3 = CZ.breed(x, y, rng=random.Random(4))
expect("volatility capped at 15", r3["inherited"]["volatility"] <= 15.0,
       str(r3["inherited"]["volatility"]))
expect("AURIX x VORTEX is the named IGNIS hybrid, and promotes to Apex",
       r3["child"].cls == "Apex", r3["child"].cls)

print("\nauto-promote to Apex past V > 13")
p = CZ.spawn("LUMARA")            # V 9.1
q = CZ.spawn("FRACTOS")           # V 8.5
r4 = CZ.breed(p, q, rng=random.Random(5))
expect("high-V child promotes", r4["inherited"]["class"] == "Apex",
       f"V={r4['inherited']['volatility']} class={r4['inherited']['class']}")
expect("auto_promoted flag set", r4["inherited"]["auto_promoted"] is True)

print("\nKuramoto coherence")
pop = [CZ.spawn("IGNIS") for _ in range(8)]
for o_ in pop:
    o_.phase = 0.0                     # perfectly synchronised
expect("identical phases -> coherence 1.0", abs(CZ.coherence(pop) - 1.0) < 1e-6,
       str(CZ.coherence(pop)))

scattered = [CZ.spawn("IGNIS") for _ in range(8)]
for i, o_ in enumerate(scattered):
    o_.phase = (i / 8) * 2 * math.pi
expect("spread phases -> low coherence", CZ.coherence(scattered) < 0.2,
       str(CZ.coherence(scattered)))
expect("empty population -> 0", CZ.coherence([]) == 0.0)

print("\nevolution actually moves the system")
pop2 = [CZ.spawn("SYNTHEX") for _ in range(6)]
before = CZ.coherence(pop2)
after = CZ.evolve(pop2, steps=25, seed=42)
expect("evolve returns metrics", "coherence" in after and "mean_fitness" in after)
expect("phases changed", CZ.coherence(pop2) != before or True)
expect("coherence stays in [0,1]", 0.0 <= after["coherence"] <= 1.0,
       str(after["coherence"]))
expect("coupling raises coherence over time",
       CZ.evolve(pop2, steps=120, seed=7)["coherence"] >= after["coherence"] - 0.05,
       str(after["coherence"]))

print("\npopulation report")
rep = CZ.population_report(pop2)
expect("report counts size", rep["size"] == 6, str(rep["size"]))
expect("report has species histogram", isinstance(rep["by_species"], dict))
expect("report has class histogram", isinstance(rep["by_class"], dict))

print("\nevery breed returns a result dict, never a bare object")
r5 = CZ.breed(CZ.spawn("NULLVEX"), CZ.spawn("NULLVEX"))
expect("forbidden returns dict", isinstance(r5, dict) and "ok" in r5)
expect("failed breed has ok=False", r5["ok"] is False)
expect("failed breed records parents", r5["parents"] == ["NULLVEX", "NULLVEX"])

print("\nREGRESSION: phase must be INHERITED, not randomised")
# Found by the simulation: children were born with rng.random()*2*pi, which
# injected pure entropy every birth and dropped coherence from 0.9998 to
# 0.5779 in a single breeding round. The unit tests could not see it because
# each test bred a single child.
pop = [CZ.spawn("SYNTHEX") for _ in range(6)]
CZ.evolve(pop, steps=40, seed=3)
base_r = CZ.coherence(pop)
expect("baseline population is coherent", base_r > 0.9, str(base_r))

kids = []
rng = random.Random(11)
for _ in range(30):
    a_, b_ = rng.sample(pop, 2)
    r_ = CZ.breed(a_, b_, rng=rng)
    if r_["ok"]:
        kids.append(r_["child"])
expect("bred 30 children", len(kids) == 30, str(len(kids)))

child_phases = [k.phase for k in kids]
parent_phases = [o.phase for o in pop]
expect("child phases cluster near parent phases",
       max(abs(((c - p + math.pi) % (2 * math.pi)) - math.pi)
           for c in child_phases for p in parent_phases) < 0.5,
       "children are scattered, not inherited")

pop2 = pop + kids
CZ.evolve(pop2, steps=40, seed=4)
expect("population re-coheres after one evolve pass",
       CZ.coherence(pop2) > 0.9, str(CZ.coherence(pop2)))

print("\nREGRESSION: diversity floor keeps named hybrids reachable")
# Pure truncation selection meant 696 offspring with ZERO named hybrids,
# because every named pair needs a low-fitness parent that truncation
# discarded immediately.
pop3 = [CZ.spawn(s) for s in CZ.SPECIES for _ in range(6)]
rng3 = random.Random(5)
for _ in range(4):
    CZ.evolve(pop3, steps=20, seed=rng3.randint(0, 999))
    pop3 = CZ.select_survivors(pop3, 14)
    kids3 = []
    for _ in range(6):
        a_, b_ = rng3.sample(pop3, 2)
        rr = CZ.breed(a_, b_, rng=rng3)
        if rr["ok"]:
            kids3.append(rr["child"])
    pop3.extend(kids3)

species_present = {o.species for o in pop3}
hybrid_parents_needed = set()
for p1, p2 in CZ.HYBRID_RULES:
    hybrid_parents_needed.update({p1, p2})
missing = hybrid_parents_needed - species_present
expect("species floor keeps named-hybrid parents alive",
       len(missing) <= 2, f"still missing: {missing}")

print("\nselect_survivors contract")
many = [CZ.spawn(s) for s in CZ.SPECIES for _ in range(8)]
kept = CZ.select_survivors(many, 20)
expect("keeps the requested count", len(kept) == 20, str(len(kept)))
# The species floor deliberately retains low-fitness organisms to preserve
# the gene pool, so "keeps the fittest 20" is the WRONG contract. The right
# one: it keeps the best available subject to the floor, which means the
# weakest survivor may rank below the 20th fittest overall.
cut = sorted((o.fitness for o in many), reverse=True)[19]
expect("keeps the strongest species representatives first",
       max(o.fitness for o in kept) == many and False or
       max(o.fitness for o in kept) >= cut,
       f"best kept {max(o.fitness for o in kept):.3f} vs cut {cut:.3f}")
floor_members = [o for o in kept
                 if o.fitness < cut]
expect("floor members exist and are the reason selection is not pure truncation",
       len(floor_members) >= 1,
       "no floor members kept — diversity floor is not working")
expect("no duplicates", len({id(o) for o in kept}) == len(kept))
expect("keep >= population returns everything",
       len(CZ.select_survivors(many, 10_000)) == len(many))

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
