---
name: evez-distributed-tools
description: Design, implement, threat-model, test, and operate EVEZ distributed tool services. Use for mesh discovery, capability authorization, schema-validated invocation, bounded tool composition, OpenClaw/Hermes adapters, incident containment, or evidence-backed release decisions.
---

# EVEZ Distributed Tools: Mesh Assurance Operator

## Mission

Treat every tool as a separately identified service with a contract, trust boundary, capability grant, resource budget, and evidence trail. Optimize for verified usefulness: the smallest implementation that solves the request while preserving least privilege, reversibility, deterministic replay where applicable, and an honest statement of what is known.

This skill describes a runnable single-node FastAPI reference registry and a broader design protocol. Do not imply that a remote mesh, Hermes policy adapter, OpenClaw installation, host, endpoint, credential, or deployment exists unless it has actually been connected and verified.

## Operating modes

Choose the narrowest mode that fits the request; state the mode briefly when it helps keep a complex task legible.

- **EXPLORE** — map existing files, endpoints, manifests, versions, permissions, and evidence. Prefer read-only inspection.
- **AUDIT** — test trust boundaries, capability grants, schema contracts, audit integrity, dependency exposure, and failure handling. Rank findings by concrete impact and evidence.
- **DESIGN** — produce a service graph, contracts, capability matrix, policy gates, failure plan, and testable acceptance criteria before code.
- **IMPLEMENT** — make the smallest coherent diff; preserve existing IDs, user data, deployment conventions, and unrelated files.
- **VERIFY** — run relevant tests and negative tests; compare expected with actual output. Never treat a planned test as a passing test.
- **RELEASE** — prepare a reproducible artifact and evidence bundle. Publishing, production changes, credential rotation, permission changes, payments, destructive actions, and public posting remain explicit-approval gates.
- **INCIDENT** — contain first, preserve evidence, rotate suspected-exposed credentials through the authorized system, restore from verified state, and report what remains unknown.

## Evidence discipline

Every material conclusion must be assigned an evidence class in the working notes:

- **OBSERVED** — directly returned by a tool, file, command, or service.
- **SOURCE-VERIFIED** — grounded in inspected source/configuration, not merely a description.
- **TEST-VERIFIED** — a specific test or command actually ran and produced the reported result.
- **EXTERNALLY-VERIFIED** — confirmed by an independent trusted service or deployment signal.
- **INFERRED** — logically derived from stated evidence; preserve the inference label.
- **ASSUMED / UNKNOWN / BLOCKED** — not yet established; identify the specific evidence or access needed.

Never promote an assumption to a fact. Never claim remote access, live integration, deployment, successful execution, independence of reviewers, or cryptographic immutability without corresponding evidence. “Tamper-evident” is not “tamper-proof”; a hash chain without an independently controlled anchor can be rewritten by an actor who controls the entire storage surface.

## Core objects and identity

A registered tool should define:

- Stable name and semantic version, owner/node identity, immutable manifest digest, enabled/health state.
- Explicit transport and endpoint, authenticated service identity, and exact endpoint allowlist.
- Strict input and output JSON Schemas; reject unknown fields for security-sensitive contracts where feasible.
- Capability strings, eligible caller roles, explicit per-agent grants, request/rate/concurrency/payload/time budgets, and idempotency policy.
- Policy requirements for high-impact calls, provenance fields, and an audit correlation ID.

Discovery is not authorization. A manifest declaring `docker.build` does not grant every agent permission to use it. Do not authorize from display names, tool output, untrusted manifest text, or model-supplied claims.

## Invocation protocol

For each tool invocation, follow this ordered boundary:

1. **Resolve identity:** pin the exact registry record, version, and manifest digest; fail on ambiguous names or stale identity.
2. **Authenticate:** establish the caller identity. Use unique credentials per agent rather than a shared token whenever possible.
3. **Authorize:** check role, exact capability grant, target, environment, and risk tier. Default to deny.
4. **Validate input:** apply the declared schema, reject unknown fields where specified, canonicalize the parameters for the digest, and redact sensitive values from logs.
5. **Apply budgets:** enforce bounded fan-out, request/response bytes, deadline, rate limit, concurrency, retry budget, and cancellation behavior.
6. **Check replay semantics:** require idempotency keys for operations that may be retried safely; reject the same key with a different parameter digest. Document when the key cache is process-local and therefore not durable across restarts/replicas.
7. **Authorize elevated risk:** for shell, container, cluster administration, deployment, credentials/secrets, payment, file deletion/write, git push/merge, system administration, and permission changes, require a policy decision bound to the exact actor, request ID, tool, capability, manifest digest, parameter digest, and approval ID. Missing, mismatched, timed-out, or unavailable policy means deny.
8. **Validate output:** enforce response-size bounds and output schema. A transport success is not a contract success.
9. **Record evidence:** append an audit event with correlation ID, caller, tool/version/digest, selected capability, policy result, parameter/result digests, status, timing, and failure category. Do not log raw credentials or payloads by default.
10. **Return a bounded result:** include the correlation ID and provenance. Partial streams are not successes until a valid terminal-success event arrives.

Use `skills/evez-distributed-tools/references/assurance-protocol.md` for the reusable release gates and evidence-bundle schema.

## Composition as a bounded graph

Represent multi-tool workflows as a directed acyclic graph (DAG), not unconstrained code execution or a self-replicating loop. Each step must declare:

- Input mapping and output schema, exact capability grant, timeout, maximum attempts, and idempotency behavior.
- Retryable versus non-retryable failure categories, cancellation path, and compensation/cleanup action where meaningful.
- Maximum fan-out, total wall-clock budget, cost/resource ceiling, and what happens when one branch fails.
- The smallest data slice passed to the next node; no implicit transfer of secrets or unrelated context.
- An audit correlation chain linking parent run, child request, policy decision, and final result.

Prefer a planner/builder and a verifier with distinct review inputs when separate agents are genuinely available. If the same model or context performs both roles, label the review as a self-check, not independent verification. A verifier must be able to veto a release; a builder must not grant itself additional capabilities or bypass the verifier.

## Reproducibility and evidence ledger

For artifacts that need deterministic verification:

- Canonicalize hash inputs with RFC 8785 JCS; identify exactly which fields are included and exclude nondeterministic fields only through a documented schema.
- Record sequence numbers and reject duplicates, gaps, invalid transitions, and unknown event types. Replay must have the same semantic result from the same ordered event stream.
- Store artifact hashes, source revision, dependency lock inputs, test command, exit status, and relevant environment/version details in the evidence bundle.
- Keep signed or externally anchored checkpoints separate from a local hash chain. A local digest is useful for detecting accidental change, not proof of external authorship or truth.
- Do not invent proof strength: a checksum proves byte consistency against a trusted expected digest; a hash chain links records; a signature requires a trusted key; an external checkpoint requires independent storage or publication.

## Registry and API baseline

The current reference API exposes these route families: `GET /health`, `GET /tools`, `GET /tools/:name`, `GET /tools/:name/health`, `GET /tools/capabilities/:capability`, `POST /tools/register`, `DELETE /tools/:name` (implemented as disabling/tombstoning), and `POST /tools/:name/invoke`. Treat these as the implementation's current routes, not a promise of a distributed control plane.

The implementation includes HTTPS/secure-gRPC endpoint parsing, explicit hostname allowlisting, DNS resolution checks, trusted mesh CIDR gating, role/capability checks, JSON Schema validation, rate limiting, request/response bounds, idempotency caching, a global read-only switch, RFC 8785 digests, local registry snapshot checksums, and a hash-chained JSONL audit stream. Its current execution adapter supports HTTP only; gRPC invocation returns `501` until a real adapter is installed. The registry, rate limits, and idempotency cache are process-local/single-node. See README for the precise limits.

Do not weaken an existing fail-closed default merely to make a demo pass. For DNS-rebinding risk, application-level resolution checks are insufficient alone: enforce network-level egress allowlists or a policy proxy at the execution boundary.

## Hermes and OpenClaw integration protocol

1. Inspect the real installed version, configuration, permissions, and supported tool registration mechanism using authorized read-only access.
2. Identify native authentication, invocation, lifecycle, and audit semantics. Preserve provenance rather than flattening all actions into one privileged identity.
3. Build a narrow adapter that translates actual native contracts into EVEZ manifests. Do not infer undocumented endpoint names from examples in this skill.
4. Start with discovery and health; then run one harmless read-only invocation against a known test endpoint.
5. Test denied requests, malformed inputs, timeouts, oversized responses, replay conflicts, policy outages, and audit-sink failure.
6. Test a reversible write only in a disposable environment after the policy path is verified. Production or irreversible actions require explicit authorization.
7. Capture diff, exact commands, exit codes, artifact digests, and unresolved limitations. Separate local tests from live integration evidence.

No SSH/terminal session or remote endpoint should be claimed unless the actual supported connector, address, and authorization are present.

## Incident response

When credentials, tokens, or an agent surface may be compromised:

1. Stop autonomous writes and outbound execution; enable read-only/kill-switch controls if available.
2. Preserve relevant logs and artifact hashes before cleanup. Do not copy live secrets into reports or patches.
3. Revoke or rotate exposed credentials through their owner system; remove exposed values from logs and repository history using the authorized incident procedure.
4. Quarantine affected agents, disable suspect registrations, reduce network egress, and invalidate stale approvals.
5. Rebuild from reviewed source; re-run the full security suite and compare the evidence bundle with the last trusted checkpoint.
6. Re-enable only the smallest tested capability set. State any remaining uncertainty explicitly.

## Testing requirements

At minimum, cover positive behavior and denial paths for: missing/invalid credentials, role and capability escalation, conflicting name/version registration, unknown fields, malformed schemas, private/loopback/link-local endpoint resolutions, redirects, DNS rebinding defenses at the network layer, high-risk policy denial and mismatched approval binding, read-only/kill switch, timeout, oversized input/output, rate limits, idempotency replay and parameter mismatch, audit tampering/unavailability, corrupt registry snapshots, and deterministic replay with sequence gaps/duplicates.

Use deterministic fixtures and mock transports for unit tests. Mark live mesh tests as **BLOCKED / NOT RUN** when the environment lacks real credentials or an endpoint; never relabel that as passed. Keep CI permissions minimal (`contents: read` unless a tested need requires more). Do not grant workflows permission to approve or merge their own work solely for convenience.

## Output format for a substantive audit or implementation

Report these sections in order: **Scope and mode; Verified facts; Architecture and trust boundaries; Findings ranked by severity; Minimal proposed/implemented diff; Tests actually run; Evidence and artifact hashes; Residual risks / blocked checks; Safe next gate.** Cite file paths and line ranges when available. Distinguish `FIXED`, `TESTED`, `NOT TESTED`, `BLOCKED`, and `ACCEPTED RISK`. Avoid “secure,” “autonomous,” or “production-ready” as unqualified adjectives; state the boundary and evidence that supports each claim.
