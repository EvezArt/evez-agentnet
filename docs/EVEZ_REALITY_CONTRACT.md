# EVEZ Reality Contract

AgentNet is an orchestration layer. It must not convert an agent assertion into authority merely because the assertion came from an internal agent.

For consequential actions, represent the request as an EVEZ Proof Envelope and evaluate it through the Reality Kernel before execution.

Required separation:

    CLAIM != EVIDENCE != AUTHORITY != INTENT != EFFECT

Runtime boundary:

    request -> Reality Kernel decision -> execute only when allowed
             -> observe effective outcome -> emit receipt -> Event Spine -> Ledger projection

Agent roles map cleanly to procedural boundaries:

- SCOUT/HARVEST: OBSERVE by default.
- SPINE/WITNESS/CAIN: record, inspect, and challenge.
- TRUNK: model/project state; no self-granted authority.
- DEPLOY: MUTATE_REVERSIBLE or MUTATE_IRREVERSIBLE only when explicitly granted.
- VAULT: secret custody; secrets do not count as evidence or authority.

Every denied or witness-required attempt remains in the Event Spine. The orchestrator must never delete an attempted action because it was denied.

Economic claims require a completed allowed Reality Gate receipt plus evidence. A requested amount is not realized value until execution is observed as completed.

Reference implementation:
https://github.com/EvezArt/evez-event-spine
