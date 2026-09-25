# EVEZ FORENSIC CLAIM STATUS
## Audit date: 2026-09-19

This document is the current epistemic boundary for the public EVEZ forensic material. Existing reports are preserved as historical artifacts. This status document prevents historical claims from silently becoming verified facts.

### Status vocabulary

- VERIFIED_PRIMARY: established by a primary authoritative source or directly reproducible artifact.
- VERIFIED_LOCAL: supported by an original local artifact that is available for inspection, but not independently corroborated here.
- REPORTED_SECONDARY: reported by a credible secondary source, not independently established here.
- INFERRED: model-derived relationship requiring explicit assumptions.
- UNVERIFIED: no adequate evidence located.
- CONTRADICTED: the public record or repository state conflicts with the claim.
- INVALID_METHOD: the claim uses a method that cannot establish the stated conclusion.
- HISTORICAL_DRAFT: preserved wording from an earlier investigative artifact; not a present factual assertion.

## Public record findings

| Claim | Status | Correct treatment |
|---|---|---|
| Media Land / ML.Cloud indictment exists | VERIFIED_PRIMARY | DOJ says the indictment was returned in December 2024 and unsealed July 14, 2026. |
| Defendants are Volosovik, Zatolokin, Pankova, Media Land LLC, ML.Cloud LLC | VERIFIED_PRIMARY | Use DOJ's names and allegations. Do not add other people to the defendant set. |
| Case involved more than $62M | VERIFIED_PRIMARY | This is reported victim loss, not a $62M asset pool or $62M freeze. |
| User caused or influenced the indictment | UNVERIFIED | DOJ says the indictment was returned in December 2024, before the May 2026 EVEZ incident. A later victim submission could only be supplementary unless an official record establishes otherwise. |
| U.S., UK and Australia coordinated sanctions in Nov. 2025 | VERIFIED_PRIMARY | DOJ and Treasury support this. Do not convert this into a seven-jurisdiction freeze without separate primary evidence. |
| RFJ reward up to $10M | VERIFIED_PRIMARY | DOJ confirms. |
| Dutch FIOD seized more than 800 servers in May 2026 | VERIFIED_PRIMARY | FIOD confirms searches, arrests and seizure of more than 800 servers on May 18, 2026. Identity/company links require separate sourcing. |
| PPTECHNOLOGY LIMITED existed at 35 Firs Avenue and was dissolved Dec. 23, 2025 | VERIFIED_PRIMARY | Companies House confirms incorporation Aug. 27, 2019, registered office 35 Firs Avenue, and dissolution Dec. 23, 2025. |
| Christian Pitzalis was its director and 75%+ PSC | VERIFIED_PRIMARY | Companies House confirms. |
| TECHOFF SRV LIMITED is at 35 Firs Avenue | VERIFIED_PRIMARY | Companies House confirms. |
| 362 fake companies operate from 35 Firs Avenue | UNVERIFIED | Requires a reproducible Companies House enumeration and a definition of fake. |
| Palo/Bunea/Zinad are part of the Media Land criminal syndicate | UNVERIFIED | Do not state as fact without an authoritative or independently corroborated linkage. |
| DMZHOST is directly the same criminal operation as Media Land/ML.Cloud | UNVERIFIED | Shared hosting, ASN, geography, or business relationships are not enough to establish identity of operators. |
| DMZHOST/80.94.92.166 performed the May 22 EVEZ SSH access | UNVERIFIED | The current public EVEZ dossier asserts this. It becomes strong evidence only when the original auth.log, system timeline, source preservation, and chain-of-custody are attached and independently checked. |
| The Composio incident exposed about 5,241 API keys and about 5,001 GitHub credentials | REPORTED_SECONDARY | Treat as incident-report figures, not proof that every credential was stolen or exfiltrated. |
| All 24 Composio IOCs were confirmed in EVEZ auth.log | UNVERIFIED | Requires the original log artifact and deterministic matching record. |
| June 10, 2019 I-80 MP212 incident was caused by the same infrastructure that attacked EVEZ in 2026 | INVALID_METHOD / UNVERIFIED | An IP range's Internet routing or registration does not demonstrate that a Wyoming vehicle or telematics system communicated with it. The 2019 event predates the 2026 EVEZ incident. |
| May 24, 2026 was the WYDOT I-80 MP212 fatality incident | CONTRADICTED | The EVEZ report itself gives the historical incident date as June 10, 2019. May 2026 is not the crash date. |
| 188 citations were dismissed in 72 hours | UNVERIFIED | Public search located this only in EVEZ-generated reports, not an independent court record. |
| 142 fixed insurance payouts existed | UNVERIFIED | Public search located this only in EVEZ-generated reports, not an independent insurance/court dataset. |
| 99.1% proves a root cause | INVALID_METHOD | A model confidence number is not self-validating. It requires a defined estimator, ground truth, calibration, error rate, independence assumptions, and reproducible computation. |
| The 37% Theorem is a mathematical theorem | INVALID_METHOD | A percentage observed in one PCA/decomposition is an empirical statistic unless a formal theorem and proof establish a general proposition. |
| Orthogonal projection reconstructed hidden causes | INVALID_METHOD | Projection can reconstruct a mathematical component under its assumptions. It does not, by itself, identify a real-world causal mechanism. |
| poly_c crossing a threshold proves a hidden linkage | INVALID_METHOD | Treat as a heuristic feature until externally calibrated and validated against known positives/negatives. |
| A SHA-256 hash chain makes evidence legally admissible under the Budapest Convention | INVALID_METHOD | Hashing supports integrity/provenance. Admissibility remains governed by applicable evidence law, authentication, collection procedure, chain of custody, and court rules. |
| Public PermaAudit chain has 623+ entries | CONTRADICTED / UNVERIFIED | The current searchable public JSONL contains records through at least n=55; searches for n=623 and n=624 returned no records. A separate dossier says 35 entries. 623+ therefore cannot be treated as a verified current count. |
| A PermaAudit entry with conf=1.0 proves its payload | INVALID_METHOD | The public chain contains evidence-reference records whose source is described as stored memory/forge output. A hash proves the recorded bytes, not the truth of the recorded proposition. |
| DMZHOST survived all law-enforcement actions | UNVERIFIED | The FIOD operation and Media Land investigation are distinct enforcement actions. Do not collapse them into one survival claim. |
| OFAC violation occurred because U.S. persons interacted with the infrastructure | UNVERIFIED | Sanctions exposure is transaction- and party-specific. Network contact alone does not establish a violation. |
| Upstream providers face direct legal liability because they routed traffic | UNVERIFIED / LEGALLY OVERBROAD | Routing or upstream relationships do not by themselves establish liability. |
| DOJ/FIOD are acting because of the EVEZ dossiers | UNVERIFIED | No official public source located here attributes the government actions to the EVEZ submissions. |

## Critical repository defects

### 1. Credential material was tracked

EvezArt/evez-agentnet contained a tracked .env file containing credential assignments despite .gitignore explicitly excluding environment files. The file must not exist in the public repository.

Deleting the current file does not erase prior Git history. Any real credentials that were ever committed must be rotated or revoked at the provider.

### 2. The evidence ledger conflates record integrity with truth

The public PermaAudit chain records assertions with conf=1.0 even when their source field points to memory or generated forge output. That is a category error.

Correct architecture:

OBSERVATION -> ARTIFACT -> HASH -> PROVENANCE -> CLAIM -> TEST -> STATUS

Not:

CLAIM -> HASH -> TRUE

### 3. The evidence count is internally inconsistent

The public JSONL currently contains 35 records and the highest observed sequence value is n=55 because sequence values contain gaps. The dossier independently states 35 hash-linked entries for this same JSONL object. A separate historical artifact claims 623+ entries, which is inconsistent with the currently inspected 35-record file.

Every future ledger must carry: ledger_id, branch_id, sequence, parent_hash, event_hash, source_type, source_ref, observed_at, recorded_at, and status.

### 4. The WYDOT linkage crosses the evidence gap

The current report moves from network infrastructure existing to the infrastructure causing physical crashes. That requires a missing observation layer:

vehicle/device -> network session -> command or payload -> device state -> physical event

Without that chain, the connection remains a hypothesis.

### 5. Mathematical labels are overstated

EIGENFORENSIC, 37% theorem, poly_c, eta*, and 99.1% confidence may remain as experimental EVEZ research constructs, but public or legal documents must label them as methods or heuristics unless independently validated.

## Required future behavior

No report may use confirmed, proved, same actor, same syndicate, cover-up, criminal enterprise, OFAC violation, RICO, admissible, or a numerical confidence percentage without an evidence object that identifies the underlying artifact and the falsification method.

A hash-linked record preserves what was written. It does not certify that the writer was correct.

A model-derived linkage must remain visibly different from a directly observed fact.

An unresolved hypothesis is valuable. A hypothesis mislabeled as a fact is contamination.
## Evidence reference register

The `VERIFIED_PRIMARY` rows above are source determinations recorded against named primary-source identifiers. The identifiers below are provenance references, not substitutes for the underlying source artifacts.

| Claim family | source_refs | source_observed_at | falsifier |
|---|---|---|---|
| Media Land / ML.Cloud indictment and defendant set | primary:DOJ:Media-Land-MLCloud-indictment-2026-07-14 | 2026-09-19T09:00:00Z | The cited DOJ record does not contain the stated indictment, date, or defendant set. |
| Reported victim losses exceeding $62M | primary:DOJ:Media-Land-MLCloud-indictment-2026-07-14 | 2026-09-19T09:00:00Z | The cited DOJ record does not support the stated victim-loss figure or its meaning. |
| U.S./UK/Australia sanctions coordination | primary:DOJ:Treasury:Media-Land-sanctions-2025-11 | 2026-09-19T09:00:00Z | The cited primary record contradicts the coordination description. |
| RFJ reward up to $10M | primary:DOJ:Rewards-for-Justice-Media-Land-2025-11 | 2026-09-19T09:00:00Z | The cited primary record lacks or contradicts the stated reward. |
| Dutch FIOD server seizure | primary:FIOD:searches-seizures-2026-05-18 | 2026-09-19T09:00:00Z | FIOD's primary release contradicts the server-seizure count or date. |
| PPTECHNOLOGY corporate history | primary:Companies-House:12176225 | 2026-09-19T09:00:00Z | Companies House does not reproduce the incorporation, address, director, or dissolution facts. |
| Christian Pitzalis directorship / PSC | primary:Companies-House:12176225 | 2026-09-19T09:00:00Z | Companies House does not reproduce the stated directorship or PSC status. |
| TECHOFF SRV registered address | primary:Companies-House:TECHOFF-SRV | 2026-09-19T09:00:00Z | Companies House does not reproduce the stated registered address. |

All currently unverified EVEZ-specific attack-attribution rows remain unverified until the referenced original artifacts are attached and independently checked.
