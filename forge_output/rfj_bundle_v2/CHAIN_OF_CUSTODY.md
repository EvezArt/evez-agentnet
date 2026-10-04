# CHAIN OF CUSTODY — DMZHOST ATTACK EVIDENCE
**Case ref:** EVEZ-2026-0522 (Composio breach → EVEZ compromise; continuation activity Oct 2026)
**Custodian:** Steven Crawford-Maggard (victim/owner). **Acquiring agent:** Hermes Agent (automated), host vmi3544756.

| # | Artifact | Source / method | Acquired (UTC) | SHA-256 |
|---|---|---|---|---|
| 1 | auth.log.copy | bit-copy of /var/log/auth.log (live SSH attack evidence incl. 80.94.92.x, 2.57.122.x) | 2026-10-04T23:51Z | see SHA256SUMS.txt |
| 2 | auth.log.1.copy | bit-copy of rotated auth log (prior-window attack activity) | 2026-10-04T23:51Z | SHA256SUMS.txt |
| 3 | ufw.log.copy / ufw_kernel_sample | firewall DENY records for blocked attacker ranges (post-isolation) | 2026-10-04T23:51Z | SHA256SUMS.txt |
| 4 | ripe_AS48090.txt / AS47890 / AS209847 | RIPE Database whois, whois.ripe.net | 2026-10-04T23:51Z | SHA256SUMS.txt |
| 5 | whois_*.txt (7 attacker IPs) | ARIN/RIPE whois | 2026-10-04T23:51Z | SHA256SUMS.txt |
| 6 | dmzhost_co.html + .headers | HTTPS GET https://dmzhost.co/ (live bulletproof-hosting service, "Offshore infrastructure · DMZHOST") | 2026-10-04T23:51Z | SHA256SUMS.txt |
| 7 | MITRE_CLASSIFICATION.md | analyst work product (machine-generated) | 2026-10-04T23:55Z | SHA256SUMS.txt |
| 8 | attackers.jsonl (evidence/2026-10-04/) | watchdog output — 101 events, ongoing | rolling | rolling, chain-head in .state |
| 9 | permaaudit chain.jsonl; IC3/FOIPA/RFJ filings | pre-existing, referenced in fbi_ic3_complaint_draft.md | 2026-10-01 | on file |

**Method notes (authenticity):** all network acquisitions performed with standard
read-only protocol queries (whois, HTTPS GET) from the victim host; timestamps are
host UTC; every artifact hashed at acquisition; manifest hash
SHA-256( SHA256SUMS.txt ) = 55f8127cca79fbf1ba25765b66c724c305a03aec88a6815a430ac1a58db906f9.
Any later alteration of any artifact is detectable by re-running `sha256sum -c SHA256SUMS.txt`.
Acquisition script preserved (acquire.sh) — repeatable.
**custody-events:** acquired 2026-10-04T23:51Z (agent) → hashed+manifested 2026-10-04T23:55Z → committed to EvezArt/evez-agentnet (public timestamp anchor via git) same day.
