# DAEMON — 24/7 Free Runtime Self-Building Agent Bus

Resolves [evez-agentnet#15](https://github.com/EvezArt/evez-agentnet/issues/15)

## Architecture

```
GitHub Issues (daemon-task)
        │
        ▼
  issue_queue.py  ──dequeue──►  loop.py  ──►  router.py (OpenRouter)
                                   │                    │
                                   ▼                    ▼
                              builder.py          free LLM models
                            (if [BUILD] task)     (mistral/gemma/llama)
                                   │
                                   ▼
                              GitHub PR  ◄─── auto-merge (swarm)
                                   │
                             spine.jsonl (append-only log)
```

## Free Runtime Strategy

| Layer | Free tier used |
|---|---|
| **Compute** | Vercel serverless (Hobby — cron every 5 min) |
| **LLM** | OpenRouter free models (mistral-7b, gemma-3-27b, llama-3.1-8b) |
| **Task queue** | GitHub Issues API (unlimited) |
| **Event log** | Vercel filesystem / GitHub repo (JSONL) |
| **Keep-alive** | GitHub Actions cron ping every 5 min |

## Setup

### 1. Vercel env vars
```
GITHUB_TOKEN=ghp_...
OPENROUTER_API_KEY=sk-or-...
DAEMON_REPO=EvezArt/evez-agentnet
```

### 2. Create a task
Open an issue in this repo with label `daemon-task`.

```
Title: Summarize recent commits in evez-agentnet
Body:  List the last 5 commits and what changed.
Label: daemon-task
```

The daemon will pick it up within 5 minutes, post a comment with the result, and close the issue.

### 3. Self-building tasks
Prefix the title with `[BUILD]`:
```
Title: [BUILD] Add rate limiter to daemon/router.py
Body:  Add a simple token-bucket rate limiter. Max 10 req/min per model.
Label: daemon-task
```
The daemon generates the code, commits it to a new branch, and opens a PR.
The swarm auto-merger (agentvault) merges it automatically.

### 4. Run locally (24/7)
```bash
export GITHUB_TOKEN=ghp_...
export OPENROUTER_API_KEY=sk-or-...
python -m daemon.loop
```

### 5. Single cycle (test)
```bash
python -m daemon.loop --once
```

## Files

| File | Purpose |
|---|---|
| `daemon/loop.py` | Main poll → process → close loop |
| `daemon/router.py` | OpenRouter free-model client |
| `daemon/issue_queue.py` | GitHub Issues as task queue |
| `daemon/builder.py` | Self-building: LLM → code → PR |
| `daemon/spine.py` | Append-only event log |
| `api/daemon.py` | Vercel serverless entry (`/api/daemon`) |
| `vercel.json` | Cron `*/5 * * * *` → `/api/daemon` |
| `.github/workflows/daemon_health.yml` | GH Actions keep-alive ping |
