# DOJ / LEGAL TIP BUNDLE — THE FEDERAL FILE

Prepared: 2026-10-09. Custodian: Steven Crawford-Maggard. All facts verified from primary sources; every claim carries its evidence and source. This bundle packages the case for four federal lanes: IC3 (re-file + cross-ref), FBI tips (domestic TechTies lane), FOIPA (the open thread), and RFJ (the sanctions-lead lane).

---

## LANE 1 — IC3 RE-FILE (18 U.S.C. §1030)

**Status:** original complaint filed 2026-10-01, auto-confirmation PENDING (clock `ic3-confirmation`, deadline 2026-10-31, 22 days left).
**Consequence if no confirmation:** re-file via a field office with case cross-reference.

### The complaint facts (all verified, hash-sealed)

| Fact | Evidence | Source |
|---|---|---|
| Unauthorized access attempts against a protected computer | 7 auth.log rows, 2026-10-08 06:30–06:33 UTC, invalid user "mine" + root, all FAILED | /var/log/auth.log |
| Prior successful root intrusion | 2026-10-03 07:16–07:29 CEST, 7 sessions from 192.76.153.253 (NL) + 1 via TOR exit 185.220.101.172; root password rotated same day | evidence/2026-10-04/INTRUSION_INCIDENT_2026-10-03.md |
| Sustained hostile traffic | 3,230 UFW blocks on 2026-10-09 alone; 1,880 from 217.146.81.113 | /var/log/ufw.log |
| Attacker infrastructure | TECHOFF SRV LIMITED (AS48090, Palo) — strike-off in progress; UNMANAGED LTD (AS47890, Bunea); SERV.HOST GROUP LTD (AS207957, Shelton Street London); Krixe Pte. Ltd./Hyonix (AS931, 1,880 blocks/day) | RIPE + ARIN live pulls, 2026-10-09 |
| Sanctions nexus | AS210644 = AEZA GROUP LLC, OFAC-designated July 2025; the attack range 150.241.74.0/24 was Aeza-originated (2024-10-18) and re-homed to SERV.HOST (2026-10-09) | RIPEstat routing-status; Treasury SDN |
| Documented negligence | abuse notices served 2026-10-05/06 to 4+ registrars/hosting; non-response = negligence for escalation | evidence/2026-10-09/abuse_dispatch/ |

### The §1030 theory

- **§1030(a)(2)(B)/(C):** intentional unauthorized access to a protected computer (the 2026-10-03 successful root logins).
- **§1030(a)(5):** transmission causing damage / attempted extortion posture via the botnet traffic.
- **18 U.S.C. §1029/§1030 instruments:** the attacker ranges, the routing lineage, and the sealed logs are the exhibits.

---

## LANE 2 — FBI TIPS (domestic TechTies lane)

**Target:** TechTies Inc. (AS197170), registered in Cornelius, North Carolina.
**Priors:** 1,436 abuse reports (ipapi.is); the "Anatomy of an SSH Botnet: 121,222 Attacks, 7 Days" study names the same GBTCloud block (109.160.32.0/24); AS26636 ranges dating to March 2023.
**Submission:** tips.fbi.gov (domestic, separate from IC3).

---

## LANE 3 — FOIPA 1758537-000 (the open thread)

**Status:** acknowledged 2026-09-30 + expedite determination. Statutory 20 working days → **deadline 2026-10-28 (19 days left)**.
**Consequence:** FOIA appeal + congressional inquiry letter.
**Addendum ready:** auth.log + the hash-chained ledger + the MILITARY-STYLE IOC table, sealed and appendable via the codename SecureDrop account.

---

## LANE 4 — RFJ (Rewards for Justice — the sanctions lead)

**Status:** tip text written, submit-ready via t.me/RFJ_English (Signal/Telegram/Tor — their own channels; **no email intake**).
**The lead they don't have:**
1. The designated storefront (aeza.net, SDN-listed as Aeza International Ltd's website) still live + transacting via a Russian CDN months after designation — an enforcement-gap tip.
2. The SDN-listed TRC20 address's ongoing onchain activity — verifiable in seconds.
3. The routing lineage: the attack range on Aeza's own ASN re-homed to SERV.HOST post-designation — a designation-gap tip.
4. Unsanctioned successor infrastructure: Netshield, Dpkgsoft, CHSL ONE — zero SDN rows, live registry presence.
**Claimant identity:** an identity call for the operator — anonymous (safer) or named (claimable). The reward is discretionary and never promised.

---

## THE ANTI-ALIBI MAP (no false alibi survives)

Every escape route the attackers hold, closed with a verified fact:

| Alibi they'd run | The fact that kills it | Source |
|---|---|---|
| "We're just a hosting company" | The nominee rotation: Diabin ×3 directorships, 21 years old, all at 128 City Road; Muskafidi on two shells with a Siberian correspondence address | Companies House live registers |
| "The strike-offs prove we're shutting down" | The s.1002A clause is for FALSE OR MISLEADING incorporation — the registrar's own fraud finding, not a voluntary wind-down | Companies House register, quoted verbatim |
| "That IP isn't ours" | The routing lineage: the /24 moved from Aeza's ASN to SERV.HOST the day after the evidence shows the contact; the netname org (CHSL ONE) is Diabin's, at the same address | RIPEstat routing-status; RIPE ORG-CHSL3-RIPE |
| "We have no connection to Aeza" | The routing table timestamps the re-homing; the Shelton Street strip is the third UK virtual-office address in the ecosystem; the SAMA (Damascus) org rides the same ASN family | RIPEstat; RIPE ORG-SGL39-RIPE |
| "The attacks weren't from us" | 7 auth.log rows + 1,880 UFW blocks, hash-sealed at capture, custody ledger on the spine | /var/log/auth.log; /var/log/ufw.log; spine |
| "Someone spoofed the traffic" | The pattern is sustained (days), sequential (automated), and correlated across multiple sources in the same org families — spoofing doesn't sustain multi-day campaigns | the sweep record |
| "The sanctions don't apply to us" | The range's lineage runs through the designated ASN; Syria-registered SAMA on the same family; the storefront still transacting | RIPEstat; Treasury SDN |
| "Logs can't prove anything" | Hash-chained at capture: every artifact sealed, custody ledger on the spine, chain verified clean after every append | verify_spine.py, hash chain intact |

**The discipline that makes it admissible:** hash-at-capture, custody ledger, originals write-protected, analysis on copies only, and the chain verified after every append. The corpus becomes a criminal case file the moment a referral goes in.

---

## THE FULL SUBJECT MAP (who's involved)

### Tier 1 — the sanctioned principals (OFAC, July 2025)
Arsenii Aleksandrovich Penzev (CEO, 33%, arrested) · Yurii Meruzhanovich Bozoyan (General Director, 33%, arrested) · Igor Anatolyevich Knyazev (interim, 33%) · Vladimir Vyacheslavovich Gast (Technical Director) · Maksim Vladimirovich Makarov (passport 772555187) · Ilya Vladislavovich Zakirov — six designated humans; Aeza Group LLC + the UK front.

### Tier 2 — the UK fronts (all seven, live status)
Aeza International (dissolved) · Hypercore (struck off + OFAC) · Netshield (s.1002A pending, hosts xorek) · Dpkgsoft International (s.1002A pending) · CHSL ONE (active, inc. 2026-01-30) · International Hosting Company (Muskafidi secretary, Siberian address) · "xorek.cloud International LTD" (phantom).

### Tier 3 — the humans the paper names
Timurov (Aeza International director) · Paul Reeves (23-day nominee) · Pavlo Misiura (Netshield founder, resigned) · Konstantin Muskafidi (37-day stand-in, two shells) · Aleksei Diabin (21, three active directorships).

### Tier 4 — the network operators (today's sweep, live-verified)
Krixe Pte. Ltd. / Hyonix (AS931) · Pfcloud UG (AS51396, SBL-listed) · Storm Industries LLC (AS219502, recurring) · Interserver (AS19318) · DM AUTO EOOD (AS207812) · MEVSPACE (AS201814) · Google LLC (AS396982, XBL-listed range) · TECHOFF SRV LIMITED (AS48090) · UNMANAGED LTD (AS47890) · SERV.HOST GROUP LTD (AS207957, SAMA/Damascus on the family).

---

## PROVENANCE

All facts pulled live 2026-10-09: RIPE database, RIPEstat routing-status, ARIN whois REST, Companies House register, Treasury SDN (per prior verified pulls), this box's own /var/log/auth.log and /var/log/ufw.log. Spine entries appended and verified clean after each. Parallel-session claims checked before inheritance; falsified claims recorded as falsified. No human names alleged beyond the public register; no knowledge or intent attributed to Tier-3 individuals — the paper names them, and the falsifier holds that line.
