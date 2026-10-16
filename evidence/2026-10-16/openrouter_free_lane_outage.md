# OpenRouter free-lane outage — 2026-10-16 (heartbeat tick diagnosis)

`openrouter-model-refresh.service` failed twice today (15:04:33 and 21:09:21 CEST)
with "No free OpenRouter candidate passed smoke test". Diagnosis below was
re-measured live this tick with the box's only OpenRouter key; no key material is
recorded here.

## Observed (all commands run 2026-10-16 ~19:40–20:00 UTC)

- Catalog API answers: 468 models, 20 free (`evidence/2026-10-16/openrouter_free_sweep.json`).
- Sweep of ALL 20 free models, one smoke request each:
  - 16 × HTTP 404 `model-ignored-by-guardrail` (configurable at
    openrouter.ai/workspaces/default/guardrails) — including
    `liquid/lfm-2.5-2.6b:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`,
    `nvidia/nemotron-3-super-120b-a12b:free`, all three of which are explicitly
    whitelisted in openclaw.json `agents.defaults.modelPolicy.allow`.
  - 2 × HTTP 403 (`thinkingmachines/inkling:free`, `thinkingmachines/inkling-small:free`).
  - 2 × server-side hang: `nvidia/nemotron-3.5-lightning:free` and
    `openrouter/free` time out at 45 s and 90 s (unit smoke budget is 20 s).
  - Alive: NONE.
- Last successful refresh was 08:56:12 UTC (backup
  `openclaw.json.pre-model-refresh-20261016085612`): even then only 2 of 19 free
  models passed smoke — the free catalog had already churned (the previous
  generation of free staples is gone from the catalog).
- Guardrail management API (`/api/v1/guardrails`, `/api/v1/workspaces`) answers
  401 with this key; `/api/v1/auth/key` confirms `is_management_key: false`.
  No management key exists on the box. Guardrail inspection/change is therefore
  dashboard-gated for the custodian.

## Impact

- openclaw-gateway stays up (peerhealth: 200) and keeps its last-good default
  primary `openrouter/nvidia/nemotron-3.5-lightning:free`, but that lane is
  currently dead server-side, so default-lane work degrades through
  `openrouter/free` (also dead) onto local `ollama/hermes3:3b`, which is loaded
  and answering. The twin's named agents (main/rogue/matt on nvidia NIM lanes)
  are unaffected.
- The systemd unit stays failed-by-truth: reset-failed would be cosmetic; the
  timer retries at 03:18 CEST and the unit self-heals if NVIDIA's free lane or
  `openrouter/free` recovers. If they do not, the lasting fix is the custodian
  reviewing the workspace guardrail in the OpenRouter dashboard (it currently
  ignores 16/20 free models, including three his own modelPolicy whitelists).

## Verdict

Upstream outage (OpenRouter workspace guardrail + dead free lanes), not a local
defect. No local remediation available with a non-management key.
