# evez-agentnet Activation Status

**Status**: WIRED — awaiting `GROQ_API_KEY` secret

## What's live
- GitHub Actions cron: `*/30 * * * *` (every 30 min, synced with hyperloop)
- Orchestrator: `scan → predict → generate → ship → earn`
- Scanner: Polymarket + GitHub trending (live), Twitter + Jobs (stubs ready)
- Predictor: Groq llama-3.3-70b-versatile (requires key)
- Generator: Gumroad reports + Twitter threads + GitHub posts
- Shipper: Twitter posting via Composio `ca_sxgQiPnjXG7g`, Gumroad log

## One required step

Add `GROQ_API_KEY` to GitHub Actions secrets:
```
https://github.com/EvezArt/evez-agentnet/settings/secrets/actions
```
Get key from: https://console.groq.com/keys

## Optional (for shipper → Twitter auto-post)
Add `TWITTER_BEARER_TOKEN` secret from https://developer.twitter.com/

## Architecture
```
orchestrator.py (every 30 min)
  scanner/scan_agent.py     → Polymarket + GitHub trending
  predictor/predict_agent.py → Groq llama-3.3-70b rank + plan
  generator/generate_agent.py → drafts/ (tweets, Gumroad reports)
  shipper/ship_agent.py      → Twitter + Gumroad + GitHub
  worldsim/                  → reputation staking (safety basin)
  spine/spine.jsonl          → immutable append-only provenance
```

*Creator: Steven Crawford-Maggard (EVEZ666) — AGPL-3.0*
