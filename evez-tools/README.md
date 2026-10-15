# EVEZ Distributed Tools

Private EVEZ Distributed Tools plugin, release **1.2.1**. This release strengthens the operator protocol for threat modeling, bounded multi-tool orchestration, evidence-backed verification, incident containment, and safe release gates. The bundled FastAPI reference runtime remains at API version **1.2.0**; its execution behavior was not changed in this documentation-and-operator-protocol release.

The plugin combines a runnable reference registry with a precise operating model for distributed agent tools. It prioritizes capability-based access, narrow service contracts, bounded invocation, policy-bound high-risk operations, deterministic hashing, and audit evidence. It does **not** by itself deploy a distributed mesh, discover reachable tools, create a Hermes approval service, open an SSH session, or prove that a remote host is available.

## What's improved in 1.2.1

- Explicit operating modes: EXPLORE, AUDIT, DESIGN, IMPLEMENT, VERIFY, RELEASE, and INCIDENT.
- Evidence classes that separate observed facts, inspected source, executed tests, external verification, inference, and unknowns.
- Bounded DAG composition with declared budgets, cancellation, retry semantics, data minimization, and parent/child correlation.
- Stronger release criteria for approvals, negative tests, recoverability, artifact digests, and residual-risk reporting.
- An incident-response sequence for containment, evidence preservation, credential rotation, quarantine, and controlled recovery.
- A reusable Mesh Assurance Protocol at `skills/evez-distributed-tools/references/assurance-protocol.md`, including change envelopes, capability ledgers, evidence bundle schema, release gates, and unattended-loop stop conditions.

## Reference implementation

- `evez_tools/app.py`: FastAPI registry with admin-gated registration/removal, per-agent capability grants, exact endpoint allowlists, DNS address checks, HTTPS-only transport, request/response limits, JSON Schema validation, rate limiting, idempotency, a global read-only switch, RFC 8785 JCS hashing, and a hash-chained JSONL audit stream. High-risk tool calls fail closed unless a configured Hermes policy adapter authorizes the exact request.
- `tests/test_registry.py`: authorization, validation, read-only, registry persistence, deterministic event replay, policy binding, idempotency, and audit checks.
- `.github/workflows/tests.yml`: CI with only `contents: read` permission.
- `Dockerfile` and `.env.example`: container baseline and configuration template.

## Local quick start

```bash
python -m pip install -e '.[test]'
export EVEZ_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export EVEZ_AGENT_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export EVEZ_TOOL_ALLOWED_HOSTS=approved-tool.example.org
export EVEZ_AGENT_GRANTS_JSON='{"agent-token":["web.search"]}'
export EVEZ_TOOLS_READONLY=1
python -m pytest -ra -vv --tb=long
uvicorn evez_tools.app:app --host 127.0.0.1 --port 8080
```

`EVEZ_TOOLS_READONLY=1` is the default and blocks tool invocation as well as registry mutation. Set it to a write-enabled value only in a controlled environment after credentials, grants, target allowlists, network policy, and approval paths are verified. Do not place live credentials in shell history, source control, manifests, evidence bundles, or logs.

## Security and deployment boundary

This is a **single-process reference**, not a production replicated mesh. The registry snapshot is local; rate limiting and idempotency state are in-process; gRPC invocation is not bundled and returns `501` until an adapter is installed. A durable deployment needs replicated state, distributed limits/idempotency, mTLS or equivalent peer identity, secret management, external/WORM audit storage, and production review.

The registry has no default outbound hosts. Configure exact destinations through `EVEZ_TOOL_ALLOWED_HOSTS`; include the Hermes policy adapter hostname in the same list. The application checks DNS results during registration and invocation, but DNS may change after validation. Enforce network-level egress allowlisting or a policy proxy to close DNS-rebinding races. Public IPs are accepted only when all resolved results are public. Private mesh peers require an exact allowlisted `*.evez.mesh` hostname plus a narrowly configured `EVEZ_MESH_CIDRS` network; do not add broad LAN CIDRs casually.

Agents require explicit per-capability grants. Prefer `EVEZ_AGENT_CREDENTIALS_JSON` with unique tokens per agent; `EVEZ_AGENT_GRANTS_JSON` scopes legacy single-token mode. Capability declarations in manifests are not grants to every caller. High-risk `shell.*`, `docker.*`, `k8s.*`, deployment, credential, payment, and write capabilities are blocked unless `EVEZ_HERMES_POLICY_URL` and a secret-managed `EVEZ_HERMES_POLICY_TOKEN` are configured. The adapter must bind and echo-match the approval ID, request ID, tool, exact capability, manifest digest, and parameter digest. No Hermes endpoint is assumed to exist until it is installed and independently verified.

The audit chain detects many accidental or post-hoc edits, but it is not proof against an attacker who can rewrite the entire file. Pair it with externally controlled or WORM storage and independently anchored checkpoints for stronger assurance. The reference HTTP executor uses request-body and output-byte limits, timeouts, no redirect following, `trust_env=False`, and a bounded process-local idempotency cache; it does not promise idempotency across restarts or multiple replicas.

## Recommended implementation loop

1. Inventory the current source, permissions, contracts, and deployment facts in read-only mode.
2. Create a narrow change envelope and list capability grants, external effects, acceptance tests, and rollback/compensation.
3. Implement the smallest coherent diff; reject unexplained permission expansion or self-approval.
4. Run deterministic unit tests plus relevant negative/security tests. Mark live integration tests `BLOCKED / NOT RUN` if no real endpoint or credentials exist.
5. Review diffs and secrets, generate artifact digests, validate audit evidence, and record residual risks.
6. Release only when the assurance gates pass; hold for unknown permissions, unbounded autonomy, failed high-risk checks, or absent recovery steps.

See `skills/evez-distributed-tools/SKILL.md` for the complete operator workflow and `skills/evez-distributed-tools/references/assurance-protocol.md` for a reusable evidence contract.
