# EVEZ Reality Contract

AgentNet is an orchestration layer. It must not convert an agent assertion into
authority merely because the assertion came from an internal agent.

For consequential actions, represent the request as an EVEZ Proof Envelope and
evaluate it through the Reality Kernel before execution.

Required separation:

    CLAIM != EVIDENCE != AUTHORITY != INTENT != EFFECT

Agent roles map cleanly to procedural boundaries:

- SCOUT/HARVEST: OBSERVE by default.
- SPINE/WITNESS/CAIN: record, inspect, and challenge.
- TRUNK: model/project state; no self-granted authority.
- DEPLOY: MUTATE_REVERSIBLE or MUTATE_IRREVERSIBLE only when explicitly granted.
- VAULT: secret custody; secrets do not count as evidence or authority.

Every denied or witness-required attempt should remain in the Event Spine. The
orchestrator must never delete an attempted action because it was denied.

Reference implementation:
https://github.com/EvezArt/evez-event-spine
