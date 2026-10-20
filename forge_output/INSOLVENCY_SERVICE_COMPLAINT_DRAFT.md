# INSOLVENCY SERVICE COMPANY-CONDUCT COMPLAINT — DRAFT (custodian submits)

Prepared 2026-10-20 ~02:50 CEST from live records. Not legal advice. Routing authority: Companies House Enforcement, Oliver, Case Manager, ref **CAS-16244-N8Z2X3/1489657**, reply of **2026-10-19**: CH holds no general investigatory powers over the conduct of companies or officers — the **Insolvency Service** (0300 678 0017) investigates corporate abuse. Your `ch-diabin-complaint` clock (CH Contact Centre deflection 2026-10-12, ref COH2382672X) records the same routing with a decision deadline of **2026-10-25**.

**Where:** gov.uk → "Complain about a limited company" → Insolvency Service company misconduct report (online form), or 0300 678 0017.

**Subject companies:** TECHOFF SRV LIMITED (16090235, director Luca Palo); BESTDC LIMITED (15259087, same director); UNMANAGED LTD (12461131, Petru-Octavian Bunea); SERV.HOST GROUP LTD (15728390, PSC/director Artem Sevastieiev); together with the CHSL ONE / NETSHIELD / DPKGSOFT entities registered through the same registered-office pattern.

---

**Complaint body (facts as documented; attach evidence on request):**

I am a US-based victim of computer intrusions executed from network infrastructure associated with the companies named above, and I report a pattern of corporate abuse in their formation and operation.

1. **Entity rotation at one registered office.** PPTechnology Limited (12176225) was dissolved 23 December 2025 — fourteen days after an Anti-Money-Laundering-supervised agent verified the director's identity there (9 December 2025). Successor entities (TECHOFF SRV LIMITED, BESTDC LIMITED) were registered to the same director through the same address pattern (35 Firs Avenue, London N11 3NE), where 61+ companies are registered.

2. **Attack from the director's network.** On 22 May 2026 an unauthorized SSH session from 80.94.92.166 — an address announced by AS48090, the network associated with TECHOFF SRV LIMITED — gained access to my systems. An FBI IC3 complaint was filed 1 October 2026 and FBI FOIPA request 1758537-000 is pending concerning the same events.

3. **Sustained attacks from UNMANAGED LTD's networks.** Networks announced by AS47890 (UNMANAGED LTD; RIPE label BUNEA-HIGH-VOLUME-NETWORK; ~2,550 IPv4 addresses) conducted 130+ authentication attacks against my systems during October 2026, kernel-logged at the time of each attempt, with a further root compromise on 3 October 2026.

4. **Criminal infrastructure on SERV.HOST space.** The range 150.241.74.0/24 (announced by AS207957, SERV.HOST GROUP LTD) attacked my systems on 8 October 2026 (logged, mitigated). The same range is documented in a third-party TLP:CLEAR threat-intelligence report (hexastrike, April 2026) as command-and-control for SmartLoader→StealC exfiltration, including a blockchain dead-drop resolver.

5. **Abuse-contact duty appears non-functional.** The published abuse contact for SERV.HOST's range (abuse@serv.host) machine-rejected my written preservation demand on all three standard channels — abuse@, noc@, postmaster@ — on 11 October 2026 (SMTP 554 5.7.1; delivery-status notifications preserved and hashed), and a re-served demand the same day has gone unanswered for over a week. On 19 October 2026 I escalated to upstream transit providers, to the Information Commission (acknowledged), and to RIPE NCC (ticket #1124364).

6. **Formal demands served and ignored.** A formal victim notice and preservation demand naming TECHOFF SRV LIMITED and demanding USD 25,000 was served 6 October 2026 (14-day period expired 20 October 2026, no response); a letter before action was served 20 October 2026. Civil proceedings in England & Wales are in preparation.

**Request:** investigation under the corporate-abuse powers Companies House identified; specific attention to the entity-rotation pattern, the identity-verification chain at the shared registered office, and the fitness of the officers named.

---

Evidence available on request: hash-chained authentication logs (SHA-256 manifest), RIPE registrations/RDAP, the 554 rejection DSNs, Companies House filing records, the served demands and their receipts, the 2026-10-19 escalation manifest (`/root/evez-agentnet/evidence/2026-10-19/servhost_escalation_sends.json`).
