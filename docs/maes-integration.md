# MAES Integration in evez-agentnet

## Overview

MAES (Modular Agent Ecology System) is registered as a first-class node in the
evez-agentnet OODA orchestrator. It provides the **agent ecology layer**: spawning,
ticking, verifying, and checkpointing agents whose behaviour feeds back into
orchestrator decisions.

## Architecture

```
evez-agentnet orchestrator.py
        │
        ├── agents/maes_connector.py      ← polls MAES /agents + /events
        │         └── observation_bus[]        ← injects into OODA Observe phase
        └── agents/maes_webhook_receiver.py ← receives EVEZ-OS FIRE events
                  └── POST MAES /oracle/ingest ← fans out to subscribed agents
```

## ENV Vars

| Var | Default | Description |
|---|---|---|
| `MAES_URL` | `https://maes.railway.app` | MAES server base URL |
| `MAES_POLL_INTERVAL` | `5` | Seconds between OODA observe ticks |

## RSI Triggers Handled

| Hypothesis | Trigger | Action |
|---|---|---|
| #3 — Ecology Scaling | 5+ verified players | Emits `scale.trigger` to bus |

## Quick Start

```bash
# Run connector standalone
python agents/maes_connector.py

# Run webhook receiver
uvicorn agents.maes_webhook_receiver:app --port 8001
```

## MAES Repo

[https://github.com/EvezArt/maes](https://github.com/EvezArt/maes)
