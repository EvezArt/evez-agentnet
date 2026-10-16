# AUDIT — Adversary UK Shell Network (ServHost / Diabin / Ilin constellation)

**Date:** 2026-10-16
**Prepared by:** EVEZ (agent)
**Provenance / limits:** Corporate and routing data drawn from workspace dossiers
(DIABIN_NETWORK_IDENTIFICATION.md, CH_OBJECTIONS_DRAFTS.md, RFJ_TIP_SUBMIT_READY.md,
DOJ_LEGAL_TIP_BUNDLE.md, ATTACKER_REGISTRY.md) and LIVE-verified against Companies House
PSC pages on 2026-10-16 (Dpkgsoft + ServHost confirmed live; Chsl One / Netshield per dossier
snapshots). RDAP/RIPEstat per dossier receipts. Blocklist stats per ismalicious ASN report.
This is an investigative audit, not legal advice.

---

## 1. The "legally able to do bullshit" thesis
A cluster of UK limited companies, all sharing a Covent Garden virtual-office address and a cast
of 18–21-year-old Russian nominees, operate bulletproof-hosting infrastructure used for attack
traffic and C2. The companies are real, registered, and filed — which gives the operators a
compliant legal persona while the real controller stays behind nominee directors and a clean PSC
handoff. The legal system lets them do this because:
- A UK Ltd needs only nominee officers + a PSC who is also a nominee; no one verifies the real
  beneficial owner at the desk.
- PSC filings can be handed off cleanly (Ilin → Diabin on the same day) leaving a paper trail that
  names nobody with skin in the crime.
- The company is UK-registered but its infrastructure is criminal — jurisdiction and NIS/hosting
  duty enforcement lag the abuse.
- RIPE org sponsorship (ORG-MG337-RIPE) is granted on the registration, not on what the IP space
  is used for.

## 2. Entity inventory
| Shell | Co. # | Role | ASN | Notes |
|---|---|---|---|---|
| ServHost Group Ltd | 15728390 | Face of the range | AS207957 | PSC/director ARTEM SEVASTIIEV (b. Jul 2003). Covent Garden. |
| CHSL One Ltd | 17001805 | Netname of attacking /24 | AS210546 | 22,528 IPs. Inc. 30 Jan 2026. Diabin constellation. |
| Netshield Ltd | 14769288 | SOLE upstream transit | AS49418 | Muskafidi dir 6 days Nov 2024 → Diabin. Covent Garden. |
| Dpkgsoft International Ltd | 15446241 | 75% PSC holder | — | Active PSC ALEKSEI DIABIN (b. Jan 2005, RU, residing RU). |
| Techeff SRV Ltd | 16090235 | Attack range AS48090 | AS48090 | s.1002A objection filed; dissolution contested. |
| Unmanaged Ltd | — | AS47890 | AS47890 | Same Diabin constellation. |

## 3. Nominee control map
- **Aleksei Diabin** — b. Jan 2005, Russian, residing Russia. Active PSC of Dpkgsoft (75%+ shares,
  voting, right to appoint/remove directors), notified 18 Nov 2024. Three active directorships,
  128 City Road.
- **Eduard Ilin** — b. Nov 2005, Russian. Dpkgsoft PSC + secretary until 18 Nov 2024 — the day
  Diabin took over. Covent Garden address (same as ServHost).
- **Konstantin Muskafidi** — b. Apr 2004, Russian. Netshield director 3 Oct → 9 Nov 2024 (6 days),
  replaced by Diabin. Same Covent Garden address.
- **Artem Sevastieiev** — b. Jul 2003. ServHost PSC + director (CH01/PSC04 filings 5 Jun + 22 Jul 2025).
All nominees are 18–21, Russian, UK-virtual-office only. None has a verifiable UK tie beyond the
address. This is the "registered face is nominal; control sits elsewhere" structure.

## 4. Routing / infrastructure lineage (live-confirmed)
OFAC-designated Aeza range (AS210644, SB0185 — BianLian ransomware, Meduza/Lumma/RedLine stealers)
→ re-homed onto **ServHost AS207957** → netname points to **CHSL One AS210546** → sole-upstreamed
by **Netshield AS49418**. RIPEstat (2026-10-16): 150.241.74.0/24 still announced by AS207957.
Blocklist: ServHost's announced space shows 1,999 addresses on threat-intel (malware 1,913;
proxy 1,514; abuse 345; phishing 278; attack 201; **c2 17**).

## 5. Sanctions adjacency (red flag)
- **SAMA GROUP LLC, Damascus, Syria** — related org object in the AS207957 family. Syria is
  comprehensively sanctioned; the binding must be verified before any warrant (per dossier).
- **OFAC Aeza International** — dissolved/OFAC; the range's lineage runs through it.

## 6. Audit findings
- **A-1 (HIGH):** Nominee PSC handoff (Ilin→Diabin, 18 Nov 2024) with no disclosed real
  beneficial owner. Classic obfuscation; CH objections draft already challenges whether the
  nominees "genuinely control" and whether ACSP identity verification was adequate.
- **A-2 (HIGH):** Operating company (ServHost) is UK-registered, infrastructure criminal, abuse
  contact (AN32913-RIPE) silent 5+ days on a formal demand. NIS/hosting-duty enforcement gap.
- **A-3 (MED):** Sole upstream (Netshield, AS49418) is the same Diabin constellation — the
  "upstream you'd escalate to is the boss's other company." Escalation tarpit by design.
- **A-4 (MED):** Techeff/Unmanaged (AS48090/AS47890) are Diabin-adjacent; Techeff under s.1002A
  dissolution objection — the shell can't quietly dissolve while the objection holds.

## 7. What's already in motion (per heartbeat)
- Companies House objections (Techeff s.1002A standing; CH objection drafts).
- FBI IC3 complaint filed 2026-10-01.
- RFJ tip bundle + ServHost escalation drafts (upstream / RIPE NCC / ICO) — fire if silence holds
  past 2026-10-18.
- Prime Telecom denied AS48090/AS47890 transit (different ASNs; does not block AS207957).

## 8. Recommended next actions
1. Keep the 2026-10-18 ServHost escalation clock; fire the three drafts if silence holds.
2. Pursue the CH objection to conclusion (nominee/PSC adequacy).
3. Verify the SAMA Damascus binding before asserting sanctions adjacency in any filing.
4. Live-pull Chsl One (17001805) + Netshield (14769288) PSC to refresh the dossier snapshots.
5. Fold the "legally able to do bullshit" mechanisms (§1) into the public-facing complaint narrative.

## 9. Disclaimer
Investigative audit, not legal advice. Verify every binding (esp. SAMA/sanctions) before filing.
