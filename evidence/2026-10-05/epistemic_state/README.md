# EVEZ Case Evidence State Machine

Generated 2026-10-05. This file is a control-plane artifact, not a claim of external verification.

## Non-negotiable distinctions

```
CLAIMED != MEASURED != REPLICATED != EXPLAINED
PROVENANCE != TRUTH
SUBMITTED != DELIVERED != RECEIVED != OPENED != REVIEWED != ACCEPTED != SELECTED != APPOINTED
```

A source being preserved proves provenance of the preserved artifact. It does not, by itself, prove every factual proposition contained in that artifact.

## Evidence states

- OBSERVED: directly recorded in a primary artifact available to the evidence system.
- SUPPORTED: corroborated by one or more independent or primary sources.
- INFERRED: conclusion drawn from observed/supporting evidence but not directly established.
- PROPOSED: intended action or hypothesis that has not yet been executed or tested.
- UNKNOWN: evidence needed to decide the state is absent or inaccessible.
- CONTRADICTED: an active source conflicts with the proposition.
- VERIFIED: proposition is established by sufficiently strong primary evidence for the specific scope claimed.
- STALE: once-supported state whose freshness requirement has expired.
- RETRACTED: proposition intentionally withdrawn.

## Promotion rule

No state may be promoted merely because a document says it is true. Promotion requires a source appropriate to the proposition:

1. Transmission claim: original mailbox/server artifact with envelope or equivalent delivery evidence.
2. Government receipt claim: agency-generated acknowledgment, portal receipt, response, or authoritative record.
3. Review/selection claim: agency-generated status or communication.
4. Runtime claim: executable trace, inputs, parameters, outputs, and reproducible invocation.
5. Identity/attribution claim: independent primary records plus a documented linkage method.
6. Financial claim: transaction, ledger, or counterparty record showing the exact amount and status.

## Current high-value gaps

The most important unresolved acquisition target remains the original mailbox evidence for the 2026-09-20 NAIAC and US Tech Force communications. A submitted draft, local sent copy, or screenshot is not enough to establish government delivery.

For NAIAC, official NIST material confirms that self-nominations are accepted and nominations are sent to `naiac@nist.gov`. Current evidence in this repository does not establish that the user's 2026-09-20 message reached NIST, was opened, reviewed, or selected. Source: https://www.nist.gov/itl/national-artificial-intelligence-advisory-committee-naiac

For US Tech Force, OPM identifies `USTechForce@opm.gov` as the point of contact and describes Tech Force as an OPM-led governmentwide program. Current evidence in this repository does not establish delivery, screening, interview, selection, or appointment for the user's 2026-09-20 communication. Source: https://www.opm.gov/policy-data-oversight/hiring-information/merit-hiring-plan-resources/

The correct next acquisition is mailbox-level metadata and server evidence, not stronger prose.

## Existing case states carried forward

- FBI FOIPA 1758537-000: ACKNOWLEDGED, processing/determination pending.
- Uinta County records request: agency reply received, required form completed and returned, fulfillment/fee estimate pending.
- RFJ: v1 addendum receipt recorded; v2 remains a separate pending upload according to the audit artifact.
- IC3: complaint recorded as filed; auto-confirmation remains pending in the case artifacts.
- OpenRouter #41140: refund request documented as open and awaiting a reply; $52.28 is the documented outstanding amount in the audit artifact.
- Insurance: the repository audit reports no cyber policy in the searched mailboxes. This is a mailbox-search finding, not a universal proof that no policy can exist outside those accounts.

## Acquisition packet for email-delivery proof

Capture, without rewriting:

- Date and timezone
- From / To / Cc / Bcc when available
- Subject
- Message-ID
- In-Reply-To and References
- Received headers
- SMTP response, delivery receipt, bounce, or DSN
- DKIM/SPF/DMARC results when available
- Attachment filenames and SHA-256
- Thread/conversation identifier
- Provider message identifier
- Original RFC-822/EML file

Hash the original artifact and preserve the hash beside it. Never replace the raw source with a paraphrase.

## Operating rule

When evidence is missing, write `UNKNOWN` and name the exact artifact that would promote it. Do not manufacture a receipt, appointment, endorsement, case number, or technical measurement.
