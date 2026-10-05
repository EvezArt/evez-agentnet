# EVEZ Project Assembly Protocol

EVEZ Foundry converts objectives into complete agentic operating environments.

## Assembly contract

Every generated operating system is an independently versioned artifact. It must have:

- a machine-readable manifest
- a boot sequence
- capability registry
- agent registry
- event/evidence spine
- memory contract
- tool contract
- authority policy
- scheduler
- health checks
- deterministic replay path where practical
- adversarial tests
- recovery procedure
- operator surface
- deployment and teardown instructions

## Assembly stages

1. DISCOVER: inspect available repositories, files, tools, runtimes, models, credentials metadata, interfaces and constraints.
2. NORMALIZE: convert discovered resources into capability records.
3. SCORE: rank capabilities by reliability, evidence quality, compatibility, cost and authority requirements.
4. COMPOSE: construct a candidate OS graph.
5. BOOT: instantiate the candidate in an isolated workspace.
6. PROBE: exercise every declared critical capability.
7. BREAK: inject controlled failures and adversarial conditions.
8. REPAIR: modify only the isolated candidate.
9. REPLAY: rerun the same evidence-producing tests.
10. WITNESS: append immutable receipts.
11. PACKAGE: produce the complete OS artifact.
12. PROMOTE: only when policy gates pass.
13. OBSERVE: collect runtime evidence.
14. RECOMPOSE: generate a new candidate when evidence shows a better architecture.

## Capability record

Each capability should expose:

- id
- name
- source repository/path
- interface
- inputs
- outputs
- dependencies
- authority level
- side effects
- evidence available
- tests available
- known failures
- reproducibility
- confidence
- last observed state

## Promotion ladder

UNKNOWN
-> OBSERVED
-> EXECUTABLE
-> TESTED
-> REPRODUCED
-> VALIDATED
-> PROMOTED

Promotion requires evidence. LLM confidence is not evidence.

## Authority levels

A0 observe
A1 derive
A2 test
A3 simulate
A4 create branch/worktree
A5 create issue
A6 propose patch
A7 modify nonproduction
A8 deploy
A9 external/irreversible action

Default autonomy ends at A5. A6+ requires explicit policy gates. A8/A9 require explicit human authorization.

## Failure doctrine

A failed test is an artifact, not something to hide.

Preserve:
- pre-state
- action
- post-state
- expected invariant
- observed invariant
- logs
- hashes
- environment
- failure classification
- repair attempt
- replay result

Never overwrite a contradictory result merely to obtain PASS.

## Completion criterion

An assembly is not complete because files were generated.

It is complete when:
- it boots,
- critical paths execute,
- failure paths have been exercised,
- evidence is preserved,
- recovery is demonstrated where applicable,
- declared interfaces match implementation,
- unsupported claims are marked UNKNOWN.

