# Connector Sovereignty

| Connector Class | Read Authority | Write Authority | Action Risk | Proof Requirement | Notes |
|---|---|---|---|---|---|
| Source truth | High | High | High | Required | repo or ledger root |
| Command surface | Medium | Medium | Medium | Required for command effects | operator entry only |
| Runtime surface | High | High | High | Required | deployment or ship path |
| Ops memory | High | Medium | Medium | Required on writes | structured operational memory |
| Telemetry | High | None | Low | Advisory only | not source truth |
| Obligation surface | Medium | Medium | Medium | Required on task creation | commitments only |
| Archive/media surface | Medium | Medium | Low | Required on writes | storage, not governance |
| Externalization surface | Medium | Medium | Medium | Required on publish | outward only |

## Governing law
Any surface that can change reality must emit enough evidence to explain what changed, when, and under whose authority.
