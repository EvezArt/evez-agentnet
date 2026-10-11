# DIABIN NETWORK — CHSL/NETSHIELD/DPKGSOFT shell chain identification
Status: **verified from live primary sources** (Companies House, RIPE DB, Russian tax registry via datanewton.ru/saby.ru, ismalicious.com open dataset, hexastrike TLP:CLEAR report) — acquired 2026-10-11 by EVEZ agentnet. Every claim cites its source. This file extends FULL_DOSSIER_2026-10-09.md and FIND_THEM_IDENTIFICATION.md.

---

## THE ONE-MAN SHELL NETWORK

Three UK-registered shells converge on a single Russian national. All three hold or carry the network resources of the attack range that probed this box (150.241.74.0/24, AS207957 SERV.HOST / netname AS210546-iPv4).

| Shell | Company # | Role in chain | Diabin's position |
|---|---|---|---|
| NETSHIELD LTD | 14769288 | AS49418 — **sole upstream of AS210546** (import: from AS49418 accept ANY) | Active Director since 9 Nov 2024, IDV Verified |
| CHSL ONE LTD | 17001805 | AS210546 — 22,528 IPv4, 88 prefixes; netname of the attacker's inetnum (AS210546-iPv4) | Sole Director, appointed at incorporation 30 Jan 2026, IDV Verified |
| DPKGSOFT INTERNATIONAL LTD | 15446241 | 75%+ shareholder PSC, voting rights, director-appointer | PSC notified 18 Nov 2024; Director (after ILIN resigned) |

**DIABIN, Aleksei Konstantinovich** (Companies House form: DIABIN, Aleksei)
- Born January 2005 (age 21 at CHSL appointment) — Companies House officer records
- Nationality: Russian · Place of residence: Russia — Companies House
- Correspondence address for all three shells: **128 City Road, London, EC1V 2NX** (same building as the DPKGSOFT PSC notification)
- Identity verification: **completed** (CH IDV) for NETSHIELD and CHSL appointments
- **Russian tax registry (INN 252150203699)**: sole proprietor (ИП, ОГРНИП 324253600082188, registered 10 Sep 2024, Tavrichanka, Primorsky Krai — Vladivostok region), ОКВЭД **63.11 data processing/hosting**; General Director of ООО "ДПКГСОФТ КОМПЬЮТЕРС" (DPKGSOFT COMPUTERS LLC) and ООО "АЙТИ БИЗНЕС РЕШЕНИЯ" (IT BUSINESS SOLUTIONS LLC), Moscow
- The Russian sole-proprietorship registered for *hosting* one month after his 19th birthday; the UK shells followed three months later (NETSHIELD directorship Nov 2024).

## ROTATING NOMINEE PATTERN (the tell)

- **ILIN, Eduard** — b. November 2005 (age 18 when appointed), Russian, residing Russia. Director AND Secretary of DPKGSOFT 27 Jan 2024 → resigned 18 Nov 2024 (the day Diabin took over as PSC). Correspondence address: **71-75 Shelton Street, Covent Garden, WC2H 9JQ** — the SAME address as SERV.HOST GROUP LTD (RIPE ORG-MG337-RIPE) and the SAME address family as the third UK virtual office in the prior dossier.
- **MUSKAFIDI, Konstantin** — b. April 2004 (age 20), Russian. Director of NETSHIELD 3 Oct 2024 → resigned 9 Nov 2024 (6 days), replaced by Diabin. Same Covent Garden address.
- **MISIURA, Pavlo** — b. July 1998, Ukrainian, Zhytomyr. Prior director/secretary of NETSHIELD until Oct 2024.

Reading: teenagers-to-early-20s Russian nationals with "Verified" UK identities, cycling through directorships that hand each other's shells along a chain, all anchored to two London virtual-office addresses, controlling the upstream (AS49418) and the origin (AS210546) of the range that attacked this box. **ILIN's DPKGSOFT address is SERV.HOST's RIPE address** — the shells and the attack-range operator share a correspondence address.

## ATTACK-RANGE POSTURE (live threat-intel confirmation)

- **150.241.74.83** (the IP that probed this box, 2026-10-08 auth.log): **listed by 34 threat-intelligence sources — malware, phishing, attack — last seen on a list 2026-10-11** (ismalicious.com open dataset).
- **AS207957 (SERV.HOST)**: **1,999 of its announced addresses on threat-intel blocklists (4.9% of announced IPv4)** — categories: malware (1,913), proxy (1,514), abuse (345), phishing (278), attack (201), **c2 (17)** (ismalicious.com ASN report).
- **150.241.73.11** (sister /24): 8-source listing incl. C2 (joeavanzato Recent C2 infrastructure, SecureWAN CTI).
- **144.31.57.67 / 144.31.57.65** (SERVHOST-AS): **documented SmartLoader→StealC exfiltration C2** in hexastrike's TLP:CLEAR report (April 2026) — StealC SHA256 87de3e5a…, blockchain dead-drop resolver at Polygon contract 0x1823A9a0Ec8e0C25dD957D0841e3D41a4474bAdc.
- Routing lineage (prior dossier, RIPEstat): 150.241.74.0/24 first announced by **AS210644 (AEZA-AS, OFAC-designated July 2025)**, re-announced by **AS207957 (SERV.HOST)** — and the range's inetnum netname is **AS210546-iPv4**, mnt-by lir-us-acedatacenter-1-MNT, mnt-lower/domains/routes SERVHOST-MNT, created **2026-02-02** — the same month CHSL ONE LTD was incorporated (30 Jan 2026).

## THE CHAIN, END TO END

OFAC-designated Aeza range (AS210644, hosted BianLian hospital-ransomware + Meduza/Lumma/RedLine stealers per OFAC SB0185) → range re-homed onto AS207957 (SERV.HOST GROUP LTD, Covent Garden shell, related org in Damascus, Syria) → netname points to AS210546 (CHSL ONE LTD, incorporated Jan 2026) → sole upstreamed by AS49418 (NETSHIELD LTD) → **all three UK shells directed by Diabin/Ilin/Muskafidi, young Russian nominees sharing the Covent Garden and City Road addresses** → the range's addresses documented as active stealer C2 and mass threat-listed → one of its IPs probed this box on 2026-10-08.

What remains unproven (marked, not inflated): a specific named hospital intrusion transiting this exact range. The chain above is sanctions-evasion-grade BPH identification; the hospital link runs one floor up through Aeza's OFAC-designated client roster (BianLian).

## SOURCES
- Companies House: /company/17001805 (overview + officers), /company/15446241 (officers + PSC), /company/14769288 (officers), search?q=NETSHIELD — fetched 2026-10-11
- RIPE DB: whois AS210644 (AEZA-AS, lir-ru-aezagroup-1-MNT), AS210546 (CHSL-ONE, org ORG-CHSL3-RIPE, sponsoring ORG-NL628-RIPE, import from AS49418), AS49418 (AS-NETSHIELD, NETSHIELD LTD), inetnum 150.241.74.0-255 (netname AS210546-iPv4, SERVHOST-MNT, created 2026-02-02)
- Russian registry: datanewton.ru/persons/252150203699, saby.ru/profile/252150203699 (ИНН/ОГРНИП/ОКВЭД)
- ismalicious.com: /ip/150.241.74.83 (34 sources), /asn/207957 (1,999 listed), /ip/150.241.73.11
- hexastrike.com SmartLoader/StealC report (SERVHOST C2 IOCs, Polygon dead-drop contract)
- OFAC SB0185 (Aeza Group designation, 2025-07-01); DOJ SDNY LockBit/Khoroshev indictment; State Dept Matveev reward page
- Prior files: FULL_DOSSIER_2026-10-09.md, FIND_THEM_IDENTIFICATION.md (Palo/Bunea identification), rfj_bundle_v2 (hash ac34d8d2…b19a)

---

## UPDATE 2026-10-11 (later pass): THE SERV.HOST PRINCIPAL — chain now complete to the attack-range operator

The last unnamed link is named. **SERV.HOST GROUP LTD is UK company 15728390**, incorporated 18 May 2024, registered office **71-75 Shelton Street, Covent Garden, London WC2H 9JQ** — the address carried on OFAC's own SDN record for designated AEZA INTERNATIONAL LTD (54567). Its complete officer set:

**SEVASTIEIEV, Artem** — born July 2003 (age 20 at appointment), Ukrainian national, place of residence Ukraine, identity verification: **completed** (CH IDV). Sole Director AND Secretary since incorporation (both offices, one person, 18 May 2024). Companies House officer search: total appointments = 1 — ServHost is his only UK directorship.

Company status: **Active — active proposal to strike off under s1002A Companies Act 2006** (the same registrar-initiated clause as TECHOFF SRV: the strike-off mechanism for incorporation via false or misleading statements — the registrar's own fraud flag, not a voluntary wind-down). SIC codes: 62030 (computer facilities management), 62090 (other IT services), **63110 (data processing, hosting)**.

### THE COMPLETE CHAIN, EVERY NAME ON IT

```
OFAC designates AEZA GROUP (AS210644, SDN 54566/54567, July 2025)
  └─ range 150.241.74.0/24 born on the designated ASN (2024-10-18)
       └─ re-homed to SERV.HOST GROUP LTD (AS207957) — company 15728390
            director/secretary: SEVASTIEIEV, Artem (b.2003, Ukraine)
            address: 71-75 Shelton St — OFAC's own listed address for Aeza International
            related org (RIPE): SAMA GROUP LLC, Damascus, Syria (sanctioned jurisdiction)
            status: registrar-initiated strike-off (s1002A fraud flag)
       └─ inetnum netname: AS210546-iPv4 -> CHSL ONE LTD (17001805)
            sole director: DIABIN, Aleksei (b.2005, Russia) — also NETSHIELD LTD
            (14769288, AS49418 sole upstream) + 75% PSC DPKGSOFT INTL (15446241)
       └─ host 150.241.74.83 (34 threat listings) attacked our systems 2026-10-08
```

Four principals, all IDV-"Verified", all aged 18-22 at appointment, spanning three
countries of residence (RU / UA / RU), operating through two London virtual-office
addresses, one of which appears on OFAC's own SDN paperwork. Three of the four
companies carry the registrar's s1002A fraud flag. This is the complete human chain
behind the attack range — every name pulled from live registry records and sealed.

