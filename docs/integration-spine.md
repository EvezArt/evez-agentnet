# Integration Spine

## Rule
No connector writes directly to another connector.
All cross-system action passes through one governor and emits a receipt.

## Hot path
Slack command -> governor -> GitHub or runtime action -> receipt -> Slack digest

## Cold path
Archive, analytics, media sync, task mirroring, externalization

## Agentnet interpretation
- source truth = repo + append-only spine
- command surface = chat, CLI, or operator-issued task
- runtime surface = generator / shipper / deployment path
- ops memory = structured tables and status artifacts
- telemetry = analytics and performance exhaust

## Why
This prevents plugin theater and keeps every side effect attributable under replay.
