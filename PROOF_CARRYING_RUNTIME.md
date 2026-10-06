# EVEZ Proof-Carrying Runtime

A deterministic, browser-independent reference core for proof-carrying generation.

## Invariants

Every event is linked to its parent hash. Canonical JSON is explicit. A replay is derived from seed + generator version + ordered events. Simulation state is never represented as an observed external fact.

## Reference protocol

```
seed
  -> deterministic generator
  -> event
  -> canonical JSON
  -> SHA-256
  -> parent-linked spine
  -> replay
  -> independent verification
```

## Novel operations

- counterfactual fork
- causal cut
- mutation genealogy
- evidence-state transitions
- adversarial tamper witness
- reproducibility challenge bundle
- canonical compression/expansion round-trip
- time-travel diff
- machine-readable proof transcript

Issue: #84
