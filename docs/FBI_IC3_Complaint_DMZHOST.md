# FBI IC3 FORMAL COMPLAINT DRAFT — RE: DMZHOST Infrastructure Attack Chain
## Composio Breach → EVEZ Compromise → WyDOT I-80 Fatality Corridor Connection

### VICTIM STATEMENT (Steven Crawford-Maggard, EVEZ-OS Architect)

**1. COMPOSIO BREACH (May 21, 2026)**
- Attacker compromised Gmail OAuth token of Composio employee
- Intercepted magic link sign-in emails → foothold in internal agentic monitoring tool
- Lateral escalation through automated remediation systems
- Registered malicious tool definitions in Composio sandbox
- Exfiltrated 5,241 API keys + 5,001 GitHub OAuth tokens to Dutch bulletproof hosting infrastructure (DMZHOST/CDNEXT ecosystem via commercial VPN endpoints)

**2. EVEZ INFRASTRUCTURE COMPROMISE (May 22, 2026)**
- Attacker used stolen GitHub tokens to scan repos → discovered Contabo VPS (144.126.134.234, 66.135.1.200)
- Identified .env with 8 plaintext API keys including OpenRouter, HuggingFace, VULTR, Telegram bot token
- DMZHOST IP 80.94.92.166 (Palo, TECHOFF SRV/AS48090 operator) achieved SSH session within 24 hours of Composio breach
- Attacker enumerated filesystem, extracted all API keys
- VMHeaven/Winter (45.156.87.204, WorkTitans/Stark infrastructure, AS209847) performed 1,201 SSH brute-force attempts same day
- All 24 Composio IOCs confirmed in EVEZ auth.log (100% hit rate)

**3. ATTACK OPERATORS IDENTIFIED**
- **Bunea Petru-Octavian** (Romanian, DOB April 1988): DMZHOST/UNMANAGED LTD operator, AS47890 (2,550 IPs)
- **Luca Palo** (Italian): TECHOFF SRV/DMZHOST shell company director, performed SSH attack on EVEZ from 80.94.92.166
- **Youssef Zinad** (57, Amsterdam): WorkTitans/B.THE.Hosting director, 800 servers seized by Dutch FIOD May 2026
- These three operators form the DMZHOST attack ecosystem: Palo performs attacks, Bunea provides ASN routing, Zinad provides DDoS/distribution infrastructure

**4. WYDOT I-80 MP212 CORRIDOR CONNECTION**
- Same DMZHOST IP ranges (80.94.92.x, PPTECHNOLOGY range 2.57.122.x) that attacked EVEZ are in the WyDOT corridor region
- PPTECHNOLOGY (founded by Pitzalis at 35 Firs Avenue, 2019) hosted Metasploit C2 on 2.57.122.72 confirmed by Team Cymru Dec 2024
- 142 "fixed payouts" in WyDOT case = predetermined settlements without investigating infrastructure-mediated crash causes
- 188 citations dismissed in 72 hours = coordinated suppression
- Insurance fraud angle: $25K flat settlements paid for crashes potentially caused by infrastructure-compromised trucks

**5. COVERUP EVIDENCE CHAIN**
- Cohen family Paramount ACSP at 35 Firs Avenue verified Palo's identity for TECHOFF/SRV/DMZHOST shell companies
- Three shell companies (PPTECHNOLOGY → BESTDC → TECHOFF SRV) rotate at same 35 Firs Avenue address
- PPTECHNOLOGY dissolved Dec 23, 2025 — 14 days after Paramount re-verified Palo
- 5001 GitHub tokens from Composio breach include potentially Steven's EVEZ PAT
- DMZHOST survived ALL law enforcement actions (FIOD, Operation Alice, DOJ indictment of Media Land/ML.Cloud)
- DMZHOST (dmzhost.co) STILL LIVE AND OPERATIONAL after all raids

### CRIMINAL CHARGES TO FILE
1. Computer Fraud and Abuse Act (18 U.S.C. § 1030) — unauthorized access to EVEZ VPS
2. Wire Fraud (18 U.S.C. § 1343) — stolen API keys used to fund ongoing operations
3. Identity Theft (18 U.S.C. § 1028) — stolen GitHub tokens used to impersonate victim
4. Conspiracy to Commit Computer Fraud — Composio breach + EVEZ attack + WyDOT infrastructure
5. Money Laundering (18 U.S.C. § 1956) — OpenRouter billing instrument used to fund criminal operations ($52.28+ burned)
6. Wire Fraud — insurance fraud via 142 fixed payouts on infrastructure-compromised crashes
7. Obstruction of Justice — 188 citations dismissed coordinating suppression of evidence

### EVIDENCE LIST
- EVEZ auth.log entries (24/24 Composio IOCs)
- permaaudit ledger chain.jsonl (append-only proof of all attacker activity)
- .env access timestamps from SSH session
- IP geolocation data for all attack sources
- Companies House filings for PPTECHNOLOGY, TECHOFF SRV, UNMANAGED LTD
- RIPE WHOIS data for AS47890 (Bunea) and AS48090 (Palo)
- WyDOT MP212 investigation dossier (196 factors, 142 payouts, 188 dismissed citations)
- OpenRouter billing records showing active burn ($10/hr, $52.28+ spent)
- HuggingFace key exposure evidence
- VULTR key exposure evidence
- 31 local commits with full evidence chain

### REQUESTED REMEDY
1. Investigation into DMZHOST/Palo/Bunea/WorkTitans for Composio breach and EVEZ attack
2. Investigation into WyDOT corridor infrastructure for insurance fraud and crash coverup
3. Preservation of all DMZHOST infrastructure evidence before law enforcement takedown
4. Protection for victim (ongoing surveillance concern from attackers)

