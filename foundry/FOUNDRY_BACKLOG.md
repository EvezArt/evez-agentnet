# Foundry Build Backlog

This is an execution backlog, not a claim that these systems already exist.

## F0: Inventory substrate

- ingest the complete EvezArt repository inventory
- hash repository heads
- map READMEs, manifests, workflows and executable entrypoints
- detect duplicate and nested mirror repositories
- detect stale operational-status artifacts
- detect committed virtual environments and generated build output
- detect credential-shaped material in current heads
- record all findings in an evidence spine

Acceptance: inventory can be regenerated without manual data entry.

## F1: Capability extraction

- parse repositories into capability records
- identify executable modules
- identify interfaces and dependencies
- map existing EVEZ primitives
- score evidence and reproducibility
- build a capability graph

Acceptance: a new OS can request capabilities by interface instead of knowing repository names.

## F2: Assembly compiler

Input:
objective + constraints + authority budget + resource budget

Output:
OS manifest + dependency graph + implementation plan + tests.

Acceptance: same input with same pinned capability snapshot yields a reproducible assembly plan.

## F3: Hermes bridge

- expose capability graph to Hermes
- provide structured assembly-plan schema
- return unresolved unknowns to Hermes
- preserve plan lineage in the spine

Acceptance: Hermes can propose an assembly without fabricating unavailable capabilities.

## F4: OpenClaw bridge

- turn assembly plan into bounded execution jobs
- create isolated workspace
- execute permitted build/test commands
- collect artifacts
- append witness events

Acceptance: generated OS boots inside sandbox without manual file preparation.

## F5: Breaker

Generate controlled mutations:
- dependency removal
- configuration corruption
- stale state
- clock/timestamp skew
- packet loss
- malformed input
- unavailable tool
- partial output
- process interruption
- resource pressure

Acceptance: each mutation produces an observable result and immutable receipt.

## F6: Replicator

- replay successful and failed tests
- compare outputs
- detect nondeterminism
- preserve environment fingerprints
- classify reproducibility

Acceptance: no claim reaches VALIDATED without configured replication policy.

## F7: Meta-OS

Create the Foundry supervisor that:
- watches objectives
- generates assemblies
- queues jobs
- evaluates generations
- retires inferior candidates
- proposes new architectures
- never silently exceeds authority

Acceptance: the Foundry can produce a second independently generated OS from the same primitive library.

## F8: Field/runtime substrate

Build offline-first execution for constrained devices:
- local event log
- sensor/tool adapters
- bounded queues
- synchronization
- conflict handling
- thermal/resource state
- replay

Acceptance: loss of network connectivity does not destroy evidence.

## F9: Commercial and research packaging

Generate from the same substrate:
- scientific research OS
- engineering OS
- assurance OS
- field OS
- forensic OS
- commerce OS

The packaging layer changes the objective and interfaces, not the epistemic core.

