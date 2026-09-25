# EVEZ Semantic PermaSignal / Human-State Machine Grammar

This layer is the communicative spine between machine observations and human-readable state.

Pipeline:

OBSERVATION -> CLASSIFY -> DISTINGUISH -> TEST -> COMMIT -> REVISE -> HANDOFF

It is intentionally not a consciousness engine, emotion detector, or autonomous authority.

## State grammar

OBSERVED = directly recorded runtime input.
SUPPORTED = independently corroborated input.
INFERRED = interpretation derived from observations.
PROPOSED = candidate explanation or action.
UNKNOWN = insufficient evidence.
INACCESSIBLE = a boundary prevented observation.
CONTRADICTED = evidence conflicts with the current representation.
STALE = once-valid state no longer current.
RETRACTED = explicitly withdrawn.

## Human-state machine

RECEIVE: accept a signal without treating it as true.
ORIENT: state what is known, unknown, and blocked.
DISTINGUISH: separate observation, inference, and proposal.
TEST: select the smallest falsifiable next check.
COMMIT: append the resulting evidence and hashes.
REVISE: preserve contradictions instead of erasing history.
HANDOFF: emit a compact state another agent or human can consume.

## Error-reduction rules

1. Never convert UNKNOWN into FACT.
2. Never convert a proposal into an observation.
3. Never delete contradictions.
4. Never claim an inaccessible surface was inspected.
5. Never treat a hash as proof that its content is true.
6. Never grant capability because a manifest merely declares it.
7. Every action recommendation must cite its triggering evidence.
8. Every derived statement must retain its parent event.
9. Every append-only event gets a previous hash and event hash.
10. Human-facing output should prefer: STATE -> EVIDENCE -> UNCERTAINTY -> NEXT TEST.

## Swarm semantics

Many agents may produce candidate atoms concurrently, but convergence occurs through deterministic normalization and evidence comparison, not through majority vote. An infinite swarm is therefore represented as an unbounded stream of bounded observations, not fabricated agent counts.

This makes the system useful even when the number of agents is unknown: the grammar remains finite, provenance remains inspectable, and uncertainty remains durable.
