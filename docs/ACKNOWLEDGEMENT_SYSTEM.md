# EVEZ Acknowledgement System

The acknowledgement layer is an epistemic control plane, not a claim generator.

Its job is to give every observed, inferred, missing, inaccessible, contradictory, or currently unresolvable thing a durable place in the map.

## Core rule

Nothing becomes true merely because the system can name it.

A record can be:
- OBSERVED: directly returned by an accessible source.
- SUPPORTED: backed by one or more independent evidence references.
- INFERRED: derived from observations; never silently promoted.
- PROPOSED: a hypothesis or planned experiment.
- UNKNOWN: relevant but unresolved.
- INACCESSIBLE: known to exist as a boundary or requested surface but not observable with current permissions/capabilities.
- CONTRADICTED: competing evidence exists.
- STALE: previously observed but not current.
- RETRACTED: explicitly withdrawn while preserving provenance.

The system also records NEGATIVE_SPACE. Negative space is not proof of absence. It is a durable statement that an expected observation, artifact, capability, relation, or protocol surface was not located under a defined search boundary.

## Acknowledgement record

Each acknowledgement should identify:
1. subject
2. state
3. observation boundary
4. evidence references
5. timestamp
6. provenance
7. falsifier or resolution condition
8. next experiment
9. capabilities required to resolve it
10. parent event

## Unacknowledgables

An "unacknowledgable" is not treated as a supernatural or hidden agent. It is an epistemic boundary: something the current system cannot responsibly assert because observation, authority, reproducibility, or interpretation is insufficient.

Examples:
- a repository path declared by metadata but not present in the inspected tree;
- an endpoint that exists but is inaccessible without authorization;
- a historical event with a claimed linkage but missing causal evidence;
- a capability declared by configuration but never demonstrated at runtime;
- a record whose source cannot be independently identified;
- two observations that cannot currently be reconciled.

These become first-class objects rather than disappearing into prose.

## Runtime loop

`DISCOVER -> ACKNOWLEDGE -> CLASSIFY -> TEST -> OBSERVE -> COMPARE -> COMMIT -> REVISE`

The acknowledgement system never authorizes an action. Authorization remains a separate capability/permission decision.

## Three ledgers

REALITY:
What was actually observed.

BOUNDARY:
What could not be observed, why, and what would be needed.

INFERENCE:
What the system currently thinks follows from the observations.

This separation prevents the common human-computer trick of turning "I cannot see it" into either "it does not exist" or "therefore it definitely exists." Civilization has suffered enough from both errors.

## Acceptance criterion

A capability is not EFFECTIVE because configuration declares it.

A capability becomes EFFECTIVE only after:
- the runtime exposes it,
- a bounded test invokes it,
- an observable result is returned,
- provenance is recorded,
- and the result can be independently checked.

A capability becomes VERIFIED only after the verification condition is satisfied and the supporting evidence is retained.

This is the acknowledgement engine: every boundary is recorded, every inference stays labeled, every contradiction survives, and every successful capability acquires a trail back to the observation that earned it.
