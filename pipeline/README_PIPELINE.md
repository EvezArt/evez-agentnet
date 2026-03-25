# EVEZ AGI Full-Stack Pipeline

**Branch:** `agi-pipeline/full-stack-integration`  
**Repo:** [EvezArt/evez-agentnet](https://github.com/EvezArt/evez-agentnet)

## Cognitive Surfaces Wired

| Surface | File | What it does |
|---|---|---|
| **OpenRouter** | `agi_orchestrator.py` | Multi-model fan-out, latency race, spine hash |
| **n8n (evez666)** | `n8n_workflow.json` | Webhook → extract best → post Slack |
| **Sentry** | `sentry_instrument.py` | Full trace + measurements per run |
| **Vercel** | `api/pipeline.py` | Serverless route, auto-deploys on push |
| **Postman** | `postman_collection.json` | 4-step end-to-end test suite |
| **Slack** | `agi_orchestrator.py` | Posts run summary to `#evez666` |
| **GitHub** | This repo | Control plane, triggers Vercel deploy |

## Required ENV Variables

```env
OPENROUTER_API_KEY=sk-or-...
N8N_WEBHOOK_URL=https://evez666.n8n.cloud/webhook/evez-agi
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SENTRY_DSN=https://...@steven-crawford-maggard.sentry.io/...
```

Set all four in **Vercel → Settings → Environment Variables** and your pipeline is live.

## Run Locally

```bash
pip install requests sentry-sdk
export OPENROUTER_API_KEY=sk-or-...
export N8N_WEBHOOK_URL=...
export SLACK_WEBHOOK_URL=...
export SENTRY_DSN=...
python pipeline/agi_orchestrator.py "Your test prompt here"
```

## Run in Postman

1. Import `pipeline/postman_collection.json` into [evezart-285668.postman.co](https://evezart-285668.postman.co)
2. Set env variables: `vercel_url`, `openrouter_key`, `N8N_WEBHOOK_URL`
3. Hit **Run Collection** → all 4 tests fire sequentially

## Flow Diagram

```
Vercel /api/pipeline
    └─► OpenRouter (multi-model fan-out)
            └─► n8n webhook (evez666)
                    └─► Slack #evez666
    └─► Sentry trace (steven-crawford-maggard.sentry.io)
```
