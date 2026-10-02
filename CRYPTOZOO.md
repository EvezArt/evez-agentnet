# EVEZ CryptoZoo — from spec to implementation

`evezx-cryptozoo` is **documentation only**. Twelve species defined, four
named hybrids, three forbidden pairings, a full inheritance table, an OODA
phase mapping — all written down, none of it ever implemented.

This is that implementation, in `evez-agentnet`.

## What it does

A Kuramoto coupled-oscillator population of twelve species. Each organism
carries `tau` (coupling period), `V` (volatility), and `gamma` (damping). The
population has a measurable order parameter `r` — 1.0 is fully synchronised,
0.0 is scattered — so "is this population healthy" is a number rather than an
assertion.

### Inheritance — implemented verbatim from BREEDING_ENGINE.md

| Trait | Rule |
|---|---|
| `tau` | average of both parents, rounded |
| `coupling` | max of both parents |
| `V` | sum of both parents, capped at 15 |
| class | auto-promote to `Apex` if V > 13 |
| skills | union of parents, capped at 4 |

### Forbidden pairings — they fail loudly

```
NULLVEX x NULLVEX  -> deadlock (duplicate parasite)
KRONOS  x ABYSSAL  -> null entity (no skills)
IGNIS   x IGNIS    -> supercritical cascade
```

`breed()` always returns a result dict. A refusal carries `ok: False` and a
reason — it never produces a silent entity.

### Named hybrids

```
FRACTOS x SYNTHEX -> NEXUS     IGNIS  x ABYSSAL -> ECLIPSE
LUMARA  x NOCTIS  -> WRAITH    AURIX  x VORTEX  -> IGNIS
```

## Two real defects the simulation found that the unit tests could not

Both were invisible to passing tests, and both were only exposed by *running*
the population.

### 1. Children were born with random phase

```python
child.phase = rng.random() * 2 * math.pi   # ← pure entropy at every birth
```

Traced: one breeding round dropped coherence from **0.9998 → 0.5779** purely
from 30 children. The oscillator physics were fine — `evolve()` restored
`r = 0.9998` in 40 steps. I initially suspected the coupling normalisation
(K_eff = mean(tau)/n, which is below K_c ≈ 0.70) and raised K; that made it
*worse*, 0.18 vs 0.9998, and proved my theory wrong.

In a coupled-oscillator model, phase is **state that damps and couples**, not
fresh noise. A child now inherits a parent's phase with a small perturbation
(`PHASE_HERITANCE_JITTER = 0.05`).

### 2. Truncation selection made every named hybrid unreachable

The first simulation bred **696 offspring and produced zero named hybrids** —
the system's most distinctive output, never occurring in practice. Cause:
every named pair needs a low-fitness parent (ABYSSAL 0.17, NOCTIS 0.28,
SYNTHEX 0.57), and pure truncation discards exactly those.

Fixed with `select_survivors()`, which reserves `species_floor` slots per
species before filling the rest on fitness. Diversity-preserving selection is
the standard approach; here it was the difference between the feature working
and being dead code.

## Measured, after the fixes

```
 gen   pop  coherence  mean_fit  hybrids
   0    72     1.0000     0.5192        0
   4    72     0.9992     0.7871        1
   8    72     0.9985     0.8229        4
  12    72     0.9987     0.8353        5

coherence : 1.000 -> 0.999     (was 0.176)
fitness   : 0.519 -> 0.835     (was 0.744, but with 0 hybrids)
hybrids   : NEXUS x24, IGNIS x5 (was none)
final     : LUMARA 15, NEXUS 14, IGNIS 12, FRACTOS 10, SYNTHEX 7, ...
```

Final population spanning seven species with named hybrids present is the
outcome the spec describes. The first implementation produced two species and
none.

## Species → agent binding

`AGENTNET_INTEGRATION.md` maps phases to species. Also unimplemented; now live:

| Phase | Species |
|---|---|
| Observe | NOCTIS, ABYSSAL |
| Orient | AURIX, VERDANT |
| Decide | FRACTOS, IGNIS |
| Act | SYNTHEX, LUMARA |

The bounds **constrain** rather than decorate: `may_publish()` denies
publication to any non-cascade species. NOCTIS (tau=3) cannot ship. That is
the whole test of whether a species mapping is real.

Two bugs found writing those tests:
- **SYNTHEX was missing from the cascade set**, so the shipper was denied
  publication — which would have silently re-broken the honesty fix earlier in
  this session. Caught only because the test asserted the shipper *can* publish.
- **Hybrid species crashed `_identity()`**. NEXUS/ECLIPSE/WRAITH are produced
  by breeding and are not in the static table. Their parameters are now
  derived from the parent pair.

## Usage

```python
import cryptozoo as CZ, agent_species as AS

a, b = CZ.spawn("SYNTHEX"), CZ.spawn("VERDANT")
r = CZ.breed(a, b)
r["child"].species, r["inherited"]["tau"]        # ('SYNTHEX', 5)

CZ.breed(CZ.spawn("IGNIS"), CZ.spawn("IGNIS"))
# {'ok': False, 'reason': 'forbidden pairing IGNIS x IGNIS: supercritical cascade ...'}

pop = [CZ.spawn(s) for s in CZ.SPECIES for _ in range(6)]
CZ.evolve(pop, steps=40)                        # Kuramoto forward
CZ.coherence(pop)                               # order parameter r

AS.assign_all()                                 # bind the 5 OODA agents
AS.may_publish("shipper")                       # (True, 'SYNTHEX (tau=6) ...')
```

CLI-free — this is a library the agentnet imports.

## Files

| File | Purpose |
|---|---|
| `cryptozoo.py` | species table, breeding, Kuramoto dynamics, coherence |
| `cryptozoo_sim.py` | full population simulation + report |
| `agent_species.py` | phase→species binding, enforcing bounds |
| `test_cryptozoo.py` | 59 assertions incl. both regressions |
| `test_agent_species.py` | 62 assertions incl. bounds enforcement |
| `diag_coherence.py`, `diag2-4.py` | the diagnosis trail for the two defects |
| `cryptozoo/simulation.json` | latest run |
| `cryptozoo/agent_species.json` | current bindings |

## Verification

```bash
python3 test_cryptozoo.py        # 59/59
python3 test_agent_species.py    # 62/62
python3 cryptozoo_sim.py         # asserts viable population, exits 1 otherwise
```
