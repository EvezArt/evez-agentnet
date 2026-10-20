# E&W CLAIM PACK — CRAWFORD-MAGGARD v UNMANAGED LTD & ORS

Prepared 2026-10-20 by Hermes from live records this turn. Skeleton for claimant review and an E&W solicitor before issue. Not legal advice. Issuing = court fee + claimant's hands (standing rule). Serves the armed consequence of clock `bunea-14day-payment` (served 2026-10-06, expired 2026-10-20 unanswered).

## Parties
- **Claimant:** Steven Crawford-Maggard, individual, 66226 N Agua Dulce Dr, Desert Hot Springs, CA 92240, USA; rubikspubes69@gmail.com
- **D1:** UNMANAGED LTD, Company No. 12461131 (England & Wales), registered office [VERIFY on the public CH record before issue]
- **D2:** Petru-Octavian Bunea, director of D1 (Romanian national, DOB April 1988, UK-resident per service record) — personal joinder = counsel's call
- **D3:** BESTDC LIMITED, Company No. 15259087 — named in the served notice; basis for joinder = counsel's call

## Relief sought
USD 25,000 (≈ £19,000 at issue-date rate) + interest + costs. Quantum is the served-demand figure; itemized heads of loss (remediation, time, security hardening) = [claimant's input + counsel].

## Particulars of claim — facts skeleton (evidence-anchored)
1. D1 operates AS47890 (RIPE label BUNEA-HIGH-VOLUME-NETWORK; ~2,550 IPv4 addresses; published abuse contact abuse@bunea.eu).
2. During October 2026, hosts within networks announced by AS47890 conducted not fewer than 130 unauthorized authentication attempts against the Claimant's systems (66.135.1.200 et al.), each kernel-logged at the time of occurrence (SHA-256-chained manifest).
3. On 3 October 2026 a further unauthorized root-level compromise of the Claimant's systems occurred.
4. Context: related operator infrastructure (AS48090, associated with TECHOFF SRV LIMITED, sole director Luca Palo) executed unauthorized access on 22 May 2026. An FBI IC3 complaint was filed 1 October 2026; FBI FOIPA request 1758537-000 is pending concerning the same events.
5. On 6 October 2026 the Claimant served a formal victim notice and preservation demand on the RIPE-registered abuse contacts of the relevant networks (dmzhostabuse@gmail.com; cc abuse@bunea.eu), naming D1–D3, demanding cessation, preservation, and USD 25,000 within 14 days. The period expired 20 October 2026 with no payment, undertaking, or substantive reply.
6. Preservation demands were served on GoDaddy, NameCheap and Cloudflare on 5 October 2026; escalations to upstream transit providers, RIPE NCC (ticket #1124364) and the Information Commission followed on 19 October 2026.
7. Continuing conduct after written notice is an aggravating factor (18 U.S.C. §1030(c)(3)(A) context; UK Computer Misuse Act 1990 equivalence) and grounds aggravated damages.

## Causes of action [FOR COUNSEL TO SETTLE]
- Negligence in the operation of the D1 network (failure to prevent its use for attacks after notice).
- [Counsel] statutory/unlawful-access framing; heads of damage: loss of security, remediation cost, time, aggravated damages.

## Pre-action compliance
- Letter before action served 6 October 2026 via the published abuse contacts (Practice Direction on Pre-Action Conduct); no reply.
- Further LBA on TECHOFF SRV LIMITED served 20 October 2026 (separate defendant track; see TECHOFF_STRIKEOFF_EVIDENCE_PACK.md).
- [Verify current HMCTS issue fee for a ~£19k claim before issue.]

## Evidence bundle (paths on this box)
- `evidence/2026-10-04/attackers.jsonl`, kernel/auth logs + SHA-256 manifest
- `forge_output/rfj_bundle_v2/formal_victim_notice_and_preservation_demand.eml` (service proof, 6 Oct)
- `docs/forensic_dossier_standalone.md`, `docs/FBI_IC3_Complaint_DMZHOST.md`, `docs/permaaudit-chain.jsonl`
- `evidence/2026-10-19/servhost_escalation_sends.json`, `logs/enemy_clocks.log`
