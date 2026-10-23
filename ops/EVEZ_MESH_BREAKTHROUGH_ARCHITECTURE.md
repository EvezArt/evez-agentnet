# EVEZ Mesh: Hermes + OpenClaw + Telegram + Tailscale + RuView

Status: integration blueprint; adapter connections are not asserted to be live merely because this document or the health checker exists.

## Goal

Make a constrained Android phone useful as an operator console and optional observation node while moving persistent work to a Linux host. The mesh should help detect interesting, repeatable changes in measurements ("breakthrough bubbles") without presenting correlation, simulation, or a model-generated interpretation as a discovery.

"Spacelike" is treated here as a research label for cross-domain or long-baseline correlation experiments. It is not a claim of faster-than-light communication, nonlocal causation, or a violation of established physics.

## Existing deployment facts to preserve

- Galaxy A16 + Termux is the mobile operator node.
- The existing mesh branch documents a Linux relay on TCP 8788, NextClaw on 8787, and OpenClaw Gateway on 18789. Hermes is a separate configured service; do not assume it listens on 18790.
- RuView's documented host endpoint is `https://vmi3544756.mooneye-shade.ts.net`; its known service ports are HTTP/UI 3000, WebSocket 3001, and CSI UDP 5005.
- Real CSI sensing requires a compatible ESP32 CSI node sending actual frames. A healthy HTTP endpoint or simulated source does not establish that physical sensing is live.
- Keep OpenClaw authentication and device pairing enabled. Keep services private to the tailnet; do not enable Tailscale Funnel or public port forwarding as a workaround.
- Keep raw audio local by default. Only explicit, user-owned recordings may be selected for an experiment; send derived features and hashes rather than audio by default.

## Target topology

```text
Galaxy A16 / Termux
  evezctl + mobile observation daemon
  (local-first, minimal battery, hashed observations)
           | HTTPS over tailnet; authenticated requests
           v
Linux mesh host
  EVEZ relay :8788  -> append-only hash-chained evidence
           | validated, bounded task envelope
           v
OpenClaw Gateway :18789 <-> Telegram channel
           | task delegation / structured results
           v
Hermes planner / verifier (separate adapter)
           |
           +--> RuView adapter (read-only health, node status, derived sensing events)
           +--> experiment runner (predeclared hypotheses and controls)
           +--> witness ledger (claim state, provenance, hashes, reviewer decisions)
```

The diagram is a target architecture, not proof that every arrow currently works. The existing relay must validate message digests and authenticate mission submissions before it is treated as a trusted evidence source. Never let a model-generated plan bypass the policy gate to reach a shell, sensor firmware, network configuration, or another agent.

## Responsibilities and contracts

### 1. Telegram: command surface, not authority

Prefer OpenClaw's existing Telegram channel rather than running multiple competing bots. Configure a strict allowlist of numeric Telegram user/chat IDs. If a separate telemetry bot is later required, use a distinct token, allowlist, webhook secret, and rate limit.

Initial commands should be read-only:
- `/status` — report sanitized service states and last verified heartbeat.
- `/nodes` — show RuView node IDs and source status, with no personal inference.
- `/last` — summarize the last evidence receipt and its verification state.
- `/experiment <id>` — read an existing experiment definition and results.

Do not enable a free-form `/run`, arbitrary shell, device-control, or firmware-update command. Any future consequential action needs a typed schema, capability allowlist, replay protection, audit record, and explicit human confirmation. Telegram text and attachments are untrusted input.

### 2. Tailscale: private transport

- Keep service listeners on loopback where possible; use Tailscale Serve for private HTTPS access.
- Confirm the Serve mapping and endpoint from both the host and phone before debugging application code.
- Do not switch to Funnel or public binds to resolve a 502.
- Treat a 502 as an upstream/routing failure, not as proof that the agent or sensor itself is broken.
- Never put bearer tokens, cookies, API keys, or complete environment output in diagnostic logs.

### 3. Hermes and OpenClaw: planner versus executor

- Hermes may propose a structured task plan and hypotheses.
- A deterministic policy validator checks schema, scope, resource limits, and allowed operations.
- OpenClaw executes only the validated, authorized task. A model's prose is never an authorization token.
- The verifier independently checks outputs against declared acceptance criteria; it must not simply repeat the planner's conclusion.
- Stop after a bounded number of retries. On ambiguity, contradictory evidence, or missing hardware, return `UNKNOWN` or `EVIDENCE_GAP`, not a success-shaped guess.

### 4. RuView: sensing adapter, not an oracle

Read-only adapter fields should include:
- endpoint reachability and HTTP status;
- reported node identifier and source type;
- last-seen time and sequence/frame counters if the API exposes them;
- whether data is explicitly simulated, hardware-derived, or unknown;
- sensor/config version and relevant calibration interval.

Do not infer that a person is present, identify a person, or treat estimated breathing/heart-rate values as medical facts from a health endpoint alone. CSI-based estimates are experimental and can be confounded by RF conditions, motion, device placement, and other environmental changes. Keep sensitive sensing opt-in, local, purpose-limited, and visible to the people being sensed.

### 5. Breakthrough bubble: a falsifiable experiment record

Each candidate must be a versioned record with:
- `hypothesis_id`, preregistered hypothesis, predicted effect, and disconfirming result;
- data-source IDs, sensor/model versions, time window, clock-quality notes, and raw-data retention policy;
- baseline and control windows, calibration and environmental covariates;
- observed measurements and uncertainty intervals;
- artifact hashes, exact code/config versions, and reproducible commands;
- repeated-run outcomes, negative results, and independent verifier result.

A candidate progresses through:
`PROPOSED -> OBSERVED -> REPRODUCED -> INDEPENDENTLY_REVIEWED`.
Any stage may instead become `CONTRADICTED`, `INCONCLUSIVE`, or `EVIDENCE_GAP`. Never delete contradictory results to improve a score. A high coherence or anomaly score is a lead to investigate, not proof of causality. For claims involving unusual physics, require calibrated instruments, independent replication, ordinary explanations tested first, and review by qualified domain researchers.

## Security and reliability gates

1. Authenticate relay mission submissions; validate schema, body digest, timestamps, payload size, and nonce/idempotency key.
2. Use a durable replay registry for production; a process-local duplicate guard is insufficient across restarts or replicas.
3. Store append-only evidence with a hash chain and periodic externally anchored checkpoints. A hash chain detects edits relative to a trusted checkpoint; it does not prove that a sensor observation was truthful.
4. Separate read-only status permissions from task execution permissions.
5. Apply request size limits, rate limits, bounded timeouts, and a circuit breaker for unavailable services.
6. Never auto-merge code or enable unattended high-impact actions merely because tests pass. Builder and verifier identities should be separate; verifier must have read-only access until approval.
7. All test data must be labeled `SIMULATED`; no synthetic frame may register as a live physical node.

## Staged acceptance plan

### Stage A — diagnose without mutation
Run `bash ops/evez-mesh-doctor.sh` on the Linux host, then from Termux. The tool emits sanitized JSON status only. Review each check; a remote HTTP 200 does not establish hardware sensing.

### Stage B — endpoint truth
Verify:
- the phone and host are connected to the same tailnet;
- Serve points to the intended local upstream;
- RuView `/health` and `/api/v1/nodes` return expected status;
- actual ESP32 hardware appears as online and reports changing frame/sequence values;
- a simulated source is explicitly labelled simulated.

### Stage C — messaging, read-only
Send `/status` from an allowlisted Telegram account. Verify that the response matches direct host checks and contains no secrets. Then test `/nodes` and `/last`. Unknown chat IDs must be denied without executing tools.

### Stage D — experiment replay
Run a fixed, offline fixture through the planner, validator, executor stub, and independent verifier. Confirm deterministic output, duplicate rejection, contradiction preservation, and explicit unknown states. No live device control.

### Stage E — guarded live experiment
Only after A-D pass, enable one read-only, opt-in experiment with a written hypothesis, baseline/control, stop condition, retention policy, and independent reviewer. No autonomous firmware changes, public exposure, or uncontrolled collection.

## Current limitations / honest status

- This blueprint and diagnostic script do not themselves configure the live Linux host, pair Telegram, change Tailscale Serve, restart containers, or attach an ESP32.
- The phone cannot manufacture the physical CSI hardware needed for genuine CSI observations.
- A passing service check is not an independent scientific replication.
- The existing PRs remain separate workstreams; merge status and live endpoint status must be checked independently before claiming deployment success.
