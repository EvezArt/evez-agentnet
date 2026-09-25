# EVEZ Ontological Bypass

The ontological bypass is not an escape from authority or security controls. It is an escape from assuming the current representation is the correct representation.

The system distinguishes three layers:
- POLICY: what documentation says should be true.
- ENFORCED: what executable code or CI demonstrably constrains.
- GAP: where the claim and enforcement diverge.

A self-audit finding is evidence-bearing data. It may identify a contradiction without resolving it.

## Recursive loop
REALITY -> WITNESS -> MODEL -> AUDIT -> AUDIT-OF-AUDIT -> ONTOLOGICAL_BREAK -> SUCCESSOR MODEL

A successor model remains proposed until independently tested. Failed representations remain historical ancestors.

## Bypass condition
When repeated exceptions accumulate, the system should test whether the representation is wrong rather than merely adding another exception.

The bypass searches for missing distinctions, hidden authority boundaries, conflated source layers, collapsed temporal states, provenance dependencies mistaken for independence, and undocumented protocol assumptions.

The bypass does not grant capabilities, permissions, access, or authority.

## Current implementation
tools/self_audit.py compares documentation, executable implementation, schema, tests, and CI. It emits SELF_AUDIT_FINDING records and explicitly labels enforcement status.

A passing self-audit does not mean the system is correct. It means the checked claims have a traceable enforcement path.

An ONTOLOGY_BREAK_CANDIDATE remains a candidate until observation and testing discriminate among successor representations.
