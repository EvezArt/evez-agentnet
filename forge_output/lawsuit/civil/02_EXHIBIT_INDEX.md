# EXHIBIT INDEX — PARTICULARS OF CLAIM

Every exhibit is a hashed copy. `SHA256SUMS.txt` in the custody bundle carries the
authoritative digests; this index states what each exhibit PROVES, so that the
evidentiary chain from artifact to pleaded fact is explicit.

## Group A — Proving the intrusion (§4.1–4.3)
| Exhibit | Artifact | Proves |
|---|---|---|
| A1 | `auth.log.copy.gz`, `auth.log.1.copy.gz` (preserved, hashed) | Contemporaneous authentication record: 1,201 failures 22 May; seven 5–24s root sessions 3 Oct 07:16–07:21 CEST from 192.76.153.253; one 07:29 CEST session from 185.220.101.172 |
| A2 | `permaaudit-chain.jsonl` | Hash-chained internal ledger recording the state transition to unauthenticated root; chain integrity independently verifiable |
| A3 | `INTRUSION_INCIDENT_2026-10-03.md` | Contemporaneous incident determination; claimant's denial statement |
| A4 | `MITRE_CLASSIFICATION.md` | Technique-level mapping of each observed behaviour to ATT&CK |

## Group B — Proving credential access and financial loss (§4.2)
| Exhibit | Artifact | Proves |
|---|---|---|
| B1 | `openrouter_receipt_2026-10-04.eml` | Provider-issued billing record evidencing fraudulent consumption against the Claimant's account |
| B2 | `PUBLIC_EXPOSURE_AUDIT.md` | Contemporaneous audit establishing which credentials were root-readable in the session |
| B3 | Exposure ledger `evidence/<date>/exposure.jsonl` | Timestamped, per-15-minute record of credential exposure state, hash-chainable |

## Group C — Proving attribution (§4.5, §6.1)
| Exhibit | Artifact | Proves |
|---|---|---|
| C1 | `ripe_AS48090.txt`, `ripe_AS47890.txt` | RIPE registration → operator identity for the originating network |
| C2 | `bgp_he_AS48090.html`, `bgp_he_AS47890.html`, `bgp_he_AS42397_buneatelecom.html`, `bgp_he_AS62380_buneatelecom.html` | Autonomous-system routing and operator data |
| C3 | `ch_16090235_officers.html`, `ch_bestdc.html`, `ch_pptech.html`, `ch_bunea_search_p1.html` | Companies House officer filings tying the natural persons to the corporate defendants |
| C4 | `ch_12176225_officers.html`, `ch_12461131_officers.html`, `ch_15259087_officers.html` | Officer history establishing entity rotation |
| C5 | `ch_01489657_officers_paramount.html`, `ch_paramount_search.html` | Third-party attestation-chain records bearing on identity verification |
| C6 | `spamhaus_sbl_hits.txt` | Independent third-party listing of the attacking infrastructure |
| C7 | `dmzhost_co.html`, `net_257122.html`, `whois_web_dmzhost_co.html` | Hosting-provider records for the infrastructure in §6 |
| C8 | `FIND_THEM_IDENTIFICATION.md` | The identification analysis, with per-claim evidentiary basis stated |

## Group D — Continuing conduct and mitigation (§4.6–4.7)
| Exhibit | Artifact | Proves |
|---|---|---|
| D1 | `05_CH_STRIKE_OFF_OBJECTION_techoff.md` | Creditor objection lodged; continuing commercial operation |
| D2 | `LETTER_BEFORE_ACTION_Bunea_SIGN.docx` | Pre-action service; 14-day expiry computation |
| D3 | `formal_victim_notice_and_preservation_demand.eml` | Preservation demand served on a third party |
| D4 | `CHAIN_OF_CUSTODY.md` | Handling history of every artifact above |

## Group E — Evidentiary integrity
| Exhibit | Artifact | Proves |
|---|---|---|
| E1 | `SHA256SUMS.txt` | Authoritative digest manifest for Group A–D |
| E2 | `/root/evez-vault/chain.jsonl` (26 entries, verified full depth) | Independent hash chain over sealed evidence objects; tampering test executed and detected |

## Addendum — exhibits held outside this bundle
| Exhibit | Artifact | Location | Proves |
|---|---|---|---|
| F1 | `05_CH_STRIKE_OFF_OBJECTION_techoff.md` | `forge_output/lawsuit/` | Creditor objection lodged against TECHOFF SRV strike-off |
| F2 | `LETTER_BEFORE_ACTION_Bunea_SIGN.docx` | `forge_output/lawsuit/` | Pre-action letter served; 14-day period runs from service |
| F3 | `04_EXHIBIT_INDEX.md` | `forge_output/lawsuit/` | Prior index, superseded by this document |
| F4 | `bgp_he_AS48090.html`, `bgp_he_AS42397_buneatelecom.html`, `bgp_he_AS62380_buneatelecom.html` | this bundle | Routing data for the three BUNEA-related ASNs |

**Manifest status.** `SHA256SUMS.txt` (30 files) verifies with zero failures. It
supersedes `SHA256SUMS_v1_SUPERSEDED.txt`, which was written at 00:05 and had gone
stale as 23 artifacts were added — that earlier manifest is retained for chain of
custody rather than deleted. The single apparent hash mismatch against the v1
manifest was `FIND_THEM_IDENTIFICATION.md`, edited at 01:04 in the ordinary course;
no content was altered after sealing.
