# ATTACKER REGISTRY — DMZHOST ECOSYSTEM (May 21/22, 2026 attack) 
*Standing intel file. Last updated 2026-10-04T22:00Z. Watchdog: attacker_watch.py, cron */15, evidence/<date>/attackers.jsonl*

## OPERATORS
| Person | Role | Known identifiers | Status 2026-10-04 |
|---|---|---|---|
| **Luca Palo** (IT) | SSH attacker, shell director — TECHOFF SRV LIMITED (16090235), AS48090 | 80.94.92.166 attacked EVEZ 2026-05-22; identity verified by Paramount ACSP at 35 Firs Ave | Companies House **strike-off in progress** |
| **Bunea Petru-Octavian** (RO, b. 04/1988) | Bulletproof ASN routing — UNMANAGED LTD (12461131), AS47890 (2,550 IPs) | DMZHOST/UNMANAGED operator | Active |
| **Youssef Zinad** (57, Amsterdam) | DDoS/distribution — WorkTitans, B.THE.Hosting | ~800 servers seized by Dutch FIOD, May 2026 | Partially disrupted; DMZHOST survived |

## INFRASTRUCTURE STATUS (verified 2026-10-04)
- **dmzhost.co: LIVE (HTTP 200)** — survived FIOD, Operation Alice, DOJ Media Land indictment
- AS48090: still ASSIGNED to TECHOFF SRV LIMITED; abuse contact dmzhostabuse@gmail.com
- 80.94.92.166 (Palo's attack IP): not responding on :80 — host dark or filtered
- RIPE pulls Oct 2: AS48090 + AS47890 both still active and announcing

## CURRENT ACTIVITY AGAINST THIS BOX (auth.log, at blocking time 2026-10-04)
- **80.94.92.179 / .234 / .55 — 68 auth attempts, same /24 as the May 22 attacker. ACTIVE.**
- **2.57.122.x (PPTECHNOLOGY, Metasploit C2 range) — 130 attempts across 7 IPs. ACTIVE.**
- 45.156.87.209 (VMHeaven/Winter): UFW-blocked contact 2026-10-04T07:07+02:00 — documented hostile contact (ufw.log.copy).
- **ALL THREE /24s FIREWALL-BLOCKED 2026-10-04 (ufw rules 1–3, tag DMZHOST-attack-ecosystem-IOC-2026-10-04).**
- Zero successful logins from any attacker range, ever, in available logs.

## CASE FILINGS
- IC3 complaint: filed 2026-10-01, auto-confirmation pending
- FBI FOIPA 1758537-000: acknowledged 2026-09-30 + expedite determination
- RFJ tip 2026-09-21 + SecureDrop addendum 2026-10-01 (bundle SHA-256 a1789b26…8904), receipt confirmed; no analyst reply yet
- Queued addendum: auth.log + hash-chained ledger + OpenRouter billing (awaiting storage host)

## ATTRIBUTION RESOLVED — INTRUSION CONFIRMED
Victim confirmed 2026-10-04: NOT him. Root password burned → rotated same day. See evidence/2026-10-04/INTRUSION_INCIDENT_2026-10-03.md.
2026-10-03 07:16–07:29 CEST: successful root password logins, 5–24s scripted sessions, from
**192.76.153.253 (RIPE/NL, 7 sessions)** and **185.220.101.172 (TOR EXIT, 1 session)**.
Also 174.205.97.33 (Verizon wireless, Sep 27). If these were you on VPN/Tor, this entry closes.
If NOT you: the root password is burned — rotate immediately. Deciding evidence: whether you ran
commands on this box on Oct 3 ~07:16–07:29.

## STANDING DEFENSE (wired 2026-10-04)
1. ufw deny inbound from all three ecosystem /24s
2. attacker_watch.py: known-IOC hits, brute-force clusters (≥10/IP), and any successful login
   outside the authorized set (Tailscale 100.64/10 + Cloudflare front) → evidence/attackers.jsonl, cron */15
3. Known-weak posture pending decision: PermitRootLogin yes + PasswordAuthentication yes —
   this is how May 22 worked. Recommend keys-only + rotating the root password regardless of
   the Oct 3 attribution answer.

## NON-ECOSYSTEM SCANNERS (classified, not adversaries)
- 85.217.140.x/149.x (Modat B.V., NL attack-surface scanner) + 194.180.49.x: commercial scanning every ~20s, all day. Background noise; logged in ufw.log.copy. No action.

## KNOWN BLOCKED RANGES (consolidated 2026-10-12)
- 217.146.81.0/24 — Krixe Pte Ltd (SG)/Hyonix AS931: 58% of all UFW blocks Oct 9; raw-drop at kernel since Oct 12
- 31.14.32.0/24 — blocked, standing scan pressure
- 185.2.80.0/24 — blocked, standing scan pressure
- 85.217.140.0/24 + 85.217.149.0/24 — Modat B.V. commercial scanner (NL)
- 109.160.32.0/24 — GBTCloud botnet range (SSH study); 109.160.32.157 top single-IP scanner Oct 12
- 194.180.49.0/24 — MEVSPACE sp. z o.o. (PL): documented hostile scanning (registry prose, consolidated)

## CONTACT LEDGER (auto-appended)

### 2026-10-12

| Source | Strikes (24h) | First seen | Stamp | Note |
|---|---|---|---|---|
| 217.146.81.113 | 229 | 2026-10-12 | 0725f82172e9 | contact only — no attribution |
| 31.14.32.8 | 148 | 2026-10-12 | 056d7669222e | contact only — no attribution |
| 185.2.80.253 | 86 | 2026-10-12 | 9a7325f09c06 | contact only — no attribution |
| 185.2.80.252 | 69 | 2026-10-12 | c4cb907df35c | contact only — no attribution |
| 31.14.32.6 | 69 | 2026-10-12 | bef6997d749a | contact only — no attribution |
| 31.14.32.7 | 60 | 2026-10-12 | f567d2e9b970 | contact only — no attribution |
| 85.217.140.15 | 59 | 2026-10-12 | b28720681e1d | contact only — no attribution |
| 85.217.140.13 | 58 | 2026-10-12 | 29d190e42b54 | contact only — no attribution |
| 85.217.149.68 | 56 | 2026-10-12 | a3e4ba95b311 | contact only — no attribution |
| 85.217.140.45 | 55 | 2026-10-12 | 0c2d846caee1 | contact only — no attribution |
| 85.217.149.72 | 54 | 2026-10-12 | 1724e802bc0f | contact only — no attribution |
| 85.217.140.48 | 52 | 2026-10-12 | 4c9923fb22b5 | contact only — no attribution |
| 85.217.140.40 | 52 | 2026-10-12 | 86c3e9d7f1ee | contact only — no attribution |
| 85.217.140.11 | 48 | 2026-10-12 | d2fe6c23db8c | contact only — no attribution |
| 85.217.149.63 | 48 | 2026-10-12 | e5fa45d25c97 | contact only — no attribution |
| 85.217.149.74 | 47 | 2026-10-12 | 3debd59ddb86 | contact only — no attribution |
| 85.217.140.47 | 47 | 2026-10-12 | d479967fb004 | contact only — no attribution |
| 85.217.140.10 | 44 | 2026-10-12 | 56258dad7ede | contact only — no attribution |
| 85.217.149.59 | 44 | 2026-10-12 | f86c30f36734 | contact only — no attribution |
| 85.217.140.44 | 43 | 2026-10-12 | 0e7e189538fa | contact only — no attribution |
| 204.76.203.4 | 42 | 2026-10-12 | 6c3dd172c847 | contact only — no attribution |
| 85.217.140.52 | 42 | 2026-10-12 | 13af9a9690a3 | contact only — no attribution |
| 85.217.140.9 | 41 | 2026-10-12 | 765a73da95e6 | contact only — no attribution |
| 85.217.140.36 | 40 | 2026-10-12 | 1a693468c022 | contact only — no attribution |
| 79.124.62.230 | 39 | 2026-10-12 | 33df7ea3c473 | contact only — no attribution |

### 2026-10-13

| Source | Strikes (24h) | First seen | Stamp | Note |
|---|---|---|---|---|
| 85.239.151.10 | 179 | 2026-10-13 | 91dec932c285 | contact only — no attribution |
| 216.180.246.152 | 121 | 2026-10-13 | df6dc53cf401 | contact only — no attribution |
| 92.204.138.51 | 94 | 2026-10-13 | f06bb0256c31 | contact only — no attribution |
| 172.110.223.179 | 42 | 2026-10-13 | 2db068bcf934 | contact only — no attribution |
| 198.46.134.48 | 28 | 2026-10-13 | 2c09fdae2ef3 | contact only — no attribution |
| 185.224.128.16 | 27 | 2026-10-13 | 746b01ab6586 | contact only — no attribution |
| 164.92.211.98 | 27 | 2026-10-13 | 336638427190 | contact only — no attribution |
| 79.124.49.70 | 24 | 2026-10-13 | 7a0016ca522c | contact only — no attribution |
| 78.128.114.174 | 22 | 2026-10-13 | 0891e40cdd19 | contact only — no attribution |
| 78.128.114.46 | 21 | 2026-10-13 | e623eb3a0b57 | contact only — no attribution |
| 176.65.149.165 | 21 | 2026-10-13 | 976f195dc0fd | contact only — no attribution |
| 143.110.153.215 | 20 | 2026-10-13 | d1229e8b6c2c | contact only — no attribution |
| 194.122.175.208 | 19 | 2026-10-13 | 9390ac0b93ad | contact only — no attribution |
| 79.124.58.90 | 18 | 2026-10-13 | f752e32fa413 | contact only — no attribution |
| 38.103.158.153 | 18 | 2026-10-13 | 95ae09b35c62 | contact only — no attribution |
| 179.43.167.3 | 18 | 2026-10-13 | fdeb7aa39186 | contact only — no attribution |
| 193.232.68.221 | 17 | 2026-10-13 | 3f64e57dac02 | contact only — no attribution |
| 78.128.114.162 | 16 | 2026-10-13 | 329915c7848f | contact only — no attribution |
| 85.11.167.7 | 16 | 2026-10-13 | 508514a51e1d | contact only — no attribution |
| 79.124.59.78 | 16 | 2026-10-13 | 54eaaac52acd | contact only — no attribution |
| 79.124.49.90 | 15 | 2026-10-13 | 95af9ef034f9 | contact only — no attribution |
| 192.161.49.2 | 15 | 2026-10-13 | 1333a67b080c | contact only — no attribution |
| 91.92.153.208 | 14 | 2026-10-13 | cb941242751d | contact only — no attribution |
| 91.191.209.46 | 14 | 2026-10-13 | e7b1bbda0a57 | contact only — no attribution |
| 79.124.56.142 | 13 | 2026-10-13 | fb4dc51d01d5 | contact only — no attribution |

### 2026-10-14

| Source | Strikes (24h) | First seen | Stamp | Note |
|---|---|---|---|---|
| 94.154.43.215 | 148 | 2026-10-14 | 788e2bcf2ab7 | contact only — no attribution |
| 89.248.163.168 | 55 | 2026-10-14 | 5e4bcb7795d6 | contact only — no attribution |
| 110.73.215.119 | 47 | 2026-10-14 | 9836c7ccf4fb | contact only — no attribution |
| 77.91.71.27 | 32 | 2026-10-14 | f35dcb298c68 | contact only — no attribution |
| 190.211.252.4 | 30 | 2026-10-14 | 9b4fcf2ad6bc | contact only — no attribution |
| 49.158.209.91 | 26 | 2026-10-14 | ba88ce18aa2f | contact only — no attribution |
| 79.124.60.218 | 24 | 2026-10-14 | bac2efd40cad | contact only — no attribution |
| 104.248.210.24 | 17 | 2026-10-14 | 469fb2274f1b | contact only — no attribution |
| 112.111.231.171 | 15 | 2026-10-14 | 0ea098b2a7f4 | contact only — no attribution |
| 185.136.15.86 | 15 | 2026-10-14 | 788b32b1c6b8 | contact only — no attribution |
| 79.124.40.162 | 14 | 2026-10-14 | c6f622c675d1 | contact only — no attribution |
| 95.214.53.157 | 13 | 2026-10-14 | 9a03817e5ea9 | contact only — no attribution |
| 37.26.86.162 | 13 | 2026-10-14 | 161d9c5aa853 | contact only — no attribution |
