# ATTACK CLASSIFICATION — MITRE ATT&CK ENTERPRISE
## Incident: Composio breach → EVEZ VPS compromise, 2026-05-21/22. Continuation activity ongoing (see attackers.jsonl).

| Phase | Technique | ID | Evidence artifact |
|---|---|---|---|
| Initial Access | Phishing: spearphishing link (Composio employee OAuth magic-link interception) | T1566.002 | IC3 complaint §1; Composio breach disclosure |
| Initial Access | External Remote Services (SSH) — 1,201 brute-forces, 2026-05-22 | T1133 | auth.log May 2026 (see ICOCs), permaaudit chain.jsonl |
| Credential Access | Brute Force: Password Guessing | T1110.001 | auth.log May 2026; 2026-10-04 continuation (80.94.92.179 et al.) |
| Credential Access | Unsecured Credentials: credentials In Files (.env, 8 plaintext API keys) | T1552.001 | SSH session timestamps in auth.log/permaaudit |
| Discovery | System Network Connection Discovery (post-foothold enumeration) | T1046/T1016 | May 22 session activity in permaaudit ledger |
| Lateral Movement | Valid Accounts: stolen GitHub OAuth tokens (5,001 from Composio) | T1078 | Composio breach disclosure; 24/24 IOC match in EVEZ auth.log |
| Command & Control | Web/Bulletproof hosting infrastructure (DMZHOST ecosystem) | T1583.001/T1584 | ripe_AS48090/47890 captures; Companies House filings |
| Impact | Financial (burned OpenRouter credits via stolen keys, $52.28+) | T1496-adjacent | OpenRouter billing records (queued RFJ addendum) |

## ACTOR CLASSIFICATION
- Luca Palo / TECHOFF SRV (AS48090): **Direct attacker** (hands-on-keyboard SSH, 2026-05-22)
- Bunea Petru-Octavian / UNMANAGED LTD (AS47890): **Infrastructure provider — bulletproof host** (aiding & abetting; know-or-should-have-known standard)
- Youssef Zinad / WorkTitans-B.THE.Hosting: **Adjacent ecosystem operator** (FIOD-seized infrastructure, same abuse ecosystem)
- Ecosystem continues commercial operation (dmzhost.co live 2026-10-04) → pattern conduct, continuing violation, supports civil + criminal exposure

## CAUSES OF ACTION (from fbi_ic3_complaint_draft.md, preserved verbatim)
18 U.S.C. §1030 (CFAA) ×2 counts · §1343 wire fraud · §1028 identity theft · §1956 money laundering · §1956 via insurance-fraud proceeds (WyDOT corridor) · conspiracy. Civil: CFAA private right (§1030(g)), trespass to chattels, conversion, unjust enrichment.
