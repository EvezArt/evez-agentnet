# Connector Sovereignty

This document declares which connectors are sovereign, advisory, or cold-path only.

| Connector | Read Authority | Write Authority | Action Risk | Proof Requirement | Notes |
|---|---|---|---|---|---|
| GitHub | High | High | High | Required | source truth |
| Slack | Medium | Medium | Medium | Required for command effects | command surface |
| Vercel | High | High | High | Required | runtime surface |
| Airtable | High | Medium | Medium | Required on writes | ops memory |
| Amplitude | High | None | Low | Advisory only | telemetry only |
| Asana | Medium | Medium | Medium | Required on task creation | obligation surface |
| Rovo | Medium | Medium | Medium | Required on write | knowledge/task surface |
| Dropbox | Medium | Medium | Low | Required on artifact writes | cold storage |
| Cloudinary | Medium | Medium | Low | Required on media writes | media registry |
| Hugging Face | Medium | Medium | Medium | Required on publish | model/dataset edge |
| Manus | Medium | Medium | Medium | Required on externalization | presentation surface |

## Immediate law

The hot path is:

- Slack
- GitHub
- Vercel

Everything else waits until the governor, receipts, and Slack routing are stable.
