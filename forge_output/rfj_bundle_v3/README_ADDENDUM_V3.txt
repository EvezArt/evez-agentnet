RFJ ADDENDUM BUNDLE v3 — built 2026-10-11
============================================

WHAT'S NEW IN v3 (over v2, unchanged, included as the base):
1. DIABIN_NETWORK_IDENTIFICATION.md — Companies House + RIPE + Russian tax
   registry identification of the three-shell UK network behind the range
   that attacked the reporting party (150.241.74.0/24):
     - NETSHIELD LTD (14769288, AS49418 = sole upstream transit)
     - CHSL ONE LTD (17001805, AS210546 = 22,528 IPs, attacker range's
       inetnum netname)
     - DPKGSOFT INTERNATIONAL LTD (15446241, 75% PSC)
   All three converge on DIABIN, Aleksei Konstantinovich (b. Jan 2005,
   Russian national residing in Russia, INN 252150203699, Primorsky Krai
   hosting sole-proprietorship). Predecessor officers ILIN, Eduard (b.
   Nov 2005) and MUSKAFIDI, Konstantin (b. Apr 2004) rotated through the
   same Covent Garden address as SERV.HOST GROUP LTD's RIPE org record.
2. Routing lineage evidence (prior v2 + verified 2026-10-11): attacker
   range first announced by AS210644 (AEZA-AS, OFAC-designated 2025-07-01,
   host to BianLian hospital ransomware + Meduza/Lumma/RedLine stealers),
   re-announced by AS207957 (SERV.HOST GROUP LTD, related org in Damascus).
3. Live threat-intel confirmation of the attacker range: 150.241.74.83
   listed by 34 sources (malware/phishing/attack), last seen 2026-10-11;
   sister /24 flagged C2; ServHost space documented as SmartLoader/StealC
   exfiltration C2 (hexastrike TLP:CLEAR, Apr 2026).

INTEGRITY: SHA256SUMS.txt in this directory covers v3 files. v2 bundle is
included byte-identical; its sealed digest (ac34d8d2d4e20a8598098d23d3
89bcc310c2ed24373f9a99165adebe48cb19a) remains authoritative for v2
contents.

UPLOAD: via SecureDrop codename account from a personal device, never
from the VPS. UPLOAD_RITUAL.md (in v2 zip) still applies.
