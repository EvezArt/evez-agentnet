# EVEZ Agentic Operating System Foundry

Purpose: autonomously assemble entirely new agentic operating systems from reusable EVEZ capabilities, with Hermes as the reasoning architect and OpenClaw as the execution substrate.

## Core thesis

EVEZ is not the operating system. EVEZ is the foundry that discovers, composes, tests, and continuously improves operating systems.

Every generated OS is a named, versioned composition with:
- kernel contract
- capability graph
- agent roles
- memory model
- evidence model
- tool adapters
- task scheduler
- policy/authority model
- simulation environment
- tests/invariants
- deployment manifest
- recovery plan
- provenance chain

## Foundry loop

DISCOVER -> MODEL -> COMPOSE -> BOOT -> PROBE -> BREAK -> REPAIR -> REPLAY -> WITNESS -> PACKAGE -> DEPLOY -> OBSERVE -> RECOMPOSE

The loop must be autonomous within explicit authority boundaries.

## OS generation

Input:
objective + constraints + available resources + desired operating envelope

Output:
a complete repository/worktree containing:
1. boot manifest
2. kernel/runtime
3. agent registry
4. event/evidence spine
5. memory/index layer
6. tool registry
7. policy engine
8. scheduler
9. test/invariance suite
10. simulator/replay harness
11. operator interface
12. deployment/recovery artifacts
13. evidence report

## Composition primitives

KERNEL:
state machine, lifecycle, capability loading, policy gates

SPINE:
immutable event/evidence chain

MIND:
Hermes reasoning adapter

HANDS:
OpenClaw execution adapter

SENSE:
discovery and telemetry adapters

MEMORY:
local structured state + retrieval/indexing

CAIN:
contradiction engine

WITNESS:
attestation and provenance

INVARIANCE:
adversarial/property testing

SIM:
deterministic replay and failure injection

SCOUT:
resource/capability discovery

HARVEST:
artifact acquisition

CARTOGRAPHER:
dependency/failure-surface mapping

BUILDER:
code and configuration generation

CRITIC:
independent attack on generated designs

RECOVER:
rollback and repair

PUBLISH:
artifact/package generation

## Agentic OS classes

Generate specialized operating systems from the same primitives:

EVEZ-RESEARCH OS
scientific investigation, literature/data acquisition, experiment planning, reproducibility.

EVEZ-CODE OS
repository discovery, implementation, testing, debugging, refactoring, release engineering.

EVEZ-FIELD OS
offline-first sensing, telemetry, mapping, local inference, synchronization and evidence capture.

EVEZ-FORENSICS OS
artifact acquisition, chain of custody, timeline reconstruction, contradiction analysis.

EVEZ-AUTONOMY OS
agent planning, tool use, simulation, failure injection, recovery.

EVEZ-SCIENCE OS
model/experiment management, parameter provenance, simulation, independent replication.

EVEZ-COMMERCE OS
capability discovery, product assembly, qualification, evidence-backed proposals and fulfillment.

EVEZ-ORCHESTRATION OS
meta-controller that creates and manages other EVEZ operating systems.

The list is not fixed. The Foundry must be able to synthesize new classes when the objective does not fit an existing class.

## Self-improvement constraint

A generated OS may modify its own sandbox implementation only through:
proposal -> isolated branch/worktree -> tests -> invariance battery -> replay -> witness -> promotion gate.

No model output becomes truth merely because it is precise or internally coherent.

CLAIMED != MEASURED != REPLICATED != EXPLAINED
PROVENANCE != TRUTH

## Meta-OS

The highest-level product is EVEZ FOUNDRY.

Its job is to:
- inventory all existing EVEZ capabilities
- deduplicate overlapping implementations
- extract reusable interfaces
- discover missing primitives
- generate OS specifications
- delegate implementation to OpenClaw
- delegate architecture/reasoning to Hermes
- attack generated systems with CAIN and Invariance Battery
- maintain reproducible evidence
- compare generations
- retire inferior compositions
- preserve their evidence and lineage
- automatically create the next generation

## Competition objective

Do not optimize for benchmark theater.

Optimize for:
- useful work completed
- reproducibility
- recovery from failure
- evidence quality
- capability coverage
- low human intervention
- time from objective to working system
- number of independently reproduced capabilities
- reduction in unresolved unknowns

The Foundry should be able to say:

GENERATED OS: X
OBJECTIVE: Y
BOOT: PASS
CAPABILITIES: 43
AUTONOMOUS TESTS: 217
REPRODUCED: 181
CONTRADICTED: 9
UNKNOWN: 27
HUMAN GATES: 2
ROLLBACKS: 4
NEXT GENERATION: READY

## Non-negotiable security boundary

Observation, analysis, sandbox execution, branch creation and test generation may be autonomous.

Credential rotation, irreversible deletion, production deployment, financial actions, legal filings and external communications require explicit authorization.

## Design principle

Do not build one giant EVEZ application.

Build a machine that can build many operating systems.

