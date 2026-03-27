# Integration Spine

This repository now contains the first scaffold for the governed integration spine.

## Rule

No connector writes directly to another connector.
All cross-system action passes through the integration governor and emits a receipt.

## Hot Path

```text
Slack command
→ integration governor
→ GitHub or Vercel action
→ receipt
→ Slack digest
```

## Cold Path

These remain out of the hot path until the authority spine is stable:

- Airtable
- Amplitude
- Asana
- Rovo
- Dropbox
- Cloudinary
- Hugging Face
- Manus

## Why this exists

Without a governor and shared types, every plugin becomes isolated theater.
With the shared substrate, later connectors can terminate into one authority chain instead of creating parallel control surfaces.

## What was added

- `integrations/types/*`
- `integrations/registry/connector_registry.ts`
- `integrations/controller/integration_governor.ts`
- `integrations/connectors/slack_connector/adapter.ts`
- `integrations/connectors/github_connector/adapter.ts`
- `integrations/connectors/vercel_connector/adapter.ts`

## Relationship to Slack and First Harvest

Slack remains the command and digest surface.
GitHub remains source truth.
Vercel remains runtime receipt and deployment surface.
First Harvest remains the first governed skill path, and later actions from that path should terminate into the same receipt logic rather than creating a separate plugin law.
