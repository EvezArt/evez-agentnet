# EVEZ Mesh Assurance Protocol v1

This protocol is a compact acceptance contract for distributed tool changes. It is designed to be copied into an issue, pull request, runbook, or release record. Empty or unknown fields must remain explicitly empty/unknown; do not fill them with inferred successes.

## 1. Change envelope

```yaml
change_id: <stable identifier>
mode: EXPLORE | AUDIT | DESIGN | IMPLEMENT | VERIFY | RELEASE | INCIDENT
source_revision: <commit or content digest, if known>
owner: <responsible identity>
intent: <one sentence>
changed_paths: []
capabilities_required: []
capabilities_added: []
external_effects: []
risk_tier: R0_READ_ONLY | R1_REVERSIBLE | R2_HIGH_IMPACT | R3_IRREVERSIBLE_OR_PUBLIC
rollback_or_compensation: <procedure or NOT_AVAILABLE>
```

Risk labels are review aids, not authorization. R2 and R3 actions require explicit policy and approval even if a change is technically reversible.

## 2. Capability ledger

For each service, record:

| Field | Required decision |
|---|---|
| Caller identity | Unique identity or documented shared-token limitation |
| Exact capability | One capability per grant where practical |
| Target scope | Host, path, environment, namespace, repository, or account |
| Data scope | Minimum inputs/outputs required |
| Resource envelope | Deadline, retries, rate, payload and fan-out bounds |
| Approval policy | None, automatic low-risk policy, or bound human/policy approval |
| Denial behavior | Explicit status/error and an audit event |
| Revocation | How the grant, credential, or registration is disabled |

No entry means no grant. A declared capability is not a user grant. A display name is never an identity.

## 3. Required negative tests

At least one test must show each relevant boundary refusing an unsafe request:

- Invalid or missing caller identity; role/capability not granted; disabled tool.
- Input schema mismatch, undeclared capability, forbidden endpoint, redirect, and oversized payload.
- High-risk operation with no approval, unavailable policy service, wrong approval ID, changed params digest, or changed manifest digest.
- Read-only/kill switch, timeout, upstream failure, malformed output, output-schema mismatch, and response over budget.
- Duplicate or conflicting idempotency key; audit chain damage or unavailable sink; corrupt registry snapshot; replay sequence gap/duplicate.
- Any newly added autonomy loop: stop condition, maximum work budget, repeated failure breaker, and prevention of self-grant/self-release.

Mark unexecuted cases `NOT RUN` and explain the missing precondition. A mocked test proves only the mocked behavior.

## 4. Evidence bundle

```yaml
evidence_version: 1
change_id: <same identifier>
source_digest: <digest or UNKNOWN>
manifest_digest: <RFC8785-JCS SHA-256 or UNKNOWN>
artifact_digests: []
commands_run: []
results:
  passed: []
  failed: []
  not_run: []
  blocked: []
policy_decisions: []
review:
  builder: <identity or UNKNOWN>
  verifier: <identity or SELF_CHECK>
  independent_review: true | false | UNKNOWN
residual_risks: []
release_decision: ACCEPT | REJECT | HOLD
```

The digest algorithm and byte representation must be stated. Do not compare hashes produced from differently canonicalized data. Never include credentials or raw sensitive payloads in this bundle.

## 5. Release gates

A release is **ACCEPT** only when all applicable gates pass:

1. **Scope:** changed paths and external effects match the approved intent.
2. **Identity:** package name, plugin ID, source of truth, audience, and permissions are preserved unless explicitly changed.
3. **Policy:** no implicit capability grant, silent policy bypass, or missing approval binding.
4. **Tests:** relevant positive and negative tests ran; failures are fixed or an explicit hold is recorded.
5. **Audit:** log chain validates, outputs are redacted, and evidence is correlated to the source revision.
6. **Recoverability:** rollback/compensation is documented for changes that can affect external state.
7. **Truthfulness:** local tests, mocked integration, live service checks, and deployment checks are labelled separately.

Any unexplained permission expansion, secret exposure, unbounded loop, failed high-risk check, or inability to preserve required evidence is a **HOLD** condition.

## 6. Autonomy stop condition

An autonomous builder/verifier loop must have all of the following before it runs unattended:

- A maximum iteration count and wall-clock/resource budget.
- A finite acceptance predicate based on tests and evidence, not model confidence.
- A circuit breaker for repeated failures, policy denials, unexpected diffs, and missing telemetry.
- Read-only default; credentials and capabilities scoped to the specific task.
- A verifier that can reject without granting the builder extra privileges.
- No self-approval for production, payment, permission, deletion, public posting, or credential changes.
- A durable run record and a kill switch whose operation does not depend on the agent loop itself.

If any condition is absent, operate in supervised/dry-run mode and label unattended execution `BLOCKED`.
