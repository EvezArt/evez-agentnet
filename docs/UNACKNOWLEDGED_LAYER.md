# EVEZ Unacknowledged Layer

This is an instrument layer for the things agent runtimes normally collapse.

## Situated capability

A capability is represented as capability + context + authority + observation + effect.
A declaration does not prove effective operation. Effective and verified states
require bounded evidence.

## Negative space

The layer records NOT_FOUND, NOT_OBSERVED, NOT_AUTHORIZED, NOT_REACHABLE,
NOT_SUPPORTED, NOT_YET_TESTED, CONTRADICTED, STALE, and UNKNOWN.

This layer is the event-level representation of negative space. It complements, rather than replaces, the repository frontier model in docs/NEGATIVE_SPACE.md and docs/NEGATIVE_SPACE_RUNTIME.md. A negative-space record requires a boundary, a resolution condition, and a next experiment. It is not proof of absence.

## Latent requirements

Explicit intent can generate PROPOSED requirements. Each requirement carries its
trigger. Generated requirements never become observations merely because the
runtime generated them.

## Prediction and surprise

PREDICTION -> ACTION -> OBSERVATION -> ERROR -> REVISION

Expected and observed values are retained. A mismatch becomes structured
prediction error instead of a vague intelligence score.

## Ontology breaks

ONTOLOGICAL_BREAK is emitted when an observation cannot be represented without
loss under the current model. The old model remains an ancestor. The successor model remains unset until a successor is explicitly proposed and tested. Candidate distinctions are retained in the open break record.

## Witness continuity

A witness records origin, transformations, observations, contradictions, and
continuity evidence. Identity starts as a HYPOTHESIS rather than an assertion.

## Capability genealogy

A capability mutation names its parent capabilities, mutation, environment,
tests, and evidence. New abilities therefore have ancestry.

## Protocol discovery

An unfamiliar surface can be modeled as a provisional protocol. AUTHORIZE
requires authorization evidence. The layer does not grant permissions.

## Questions and scars

Unresolved questions become durable objects with resolution conditions and
required instruments. Consequential events can leave scars: state changes that
become future constraints.

## Source boundaries

Every event is labeled REAL, SIMULATED, DERIVED, HYPOTHETICAL, or CROSS_DOMAIN.
Cross-domain data cannot erase the distinction between simulation and reality.

## Append-only evidence

Events are SHA-256 content-addressed and parent-linked. Caller-supplied timestamps
make deterministic replay possible. The module is dependency-free and does not
execute arbitrary external actions.
