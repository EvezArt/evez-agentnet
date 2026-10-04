# INTRUSION INCIDENT — root compromise via password, 2026-10-03 (CONTAINED 2026-10-04)
**Victim statement (Steven Crawford-Maggard, delivered to agent 2026-10-04):** the Oct 3
root logins from 192.76.153.253 (RIPE/NL, 7 scripted sessions 07:16–07:21 CEST) and
185.220.101.172 (Tor exit RELAYON/CIA TRIAD, 1 session 07:29 CEST) were **NOT him**.
(174.205.97.33, Verizon Business wireless, 2026-09-27 — presumed his mobile path; unconfirmed.)

## Unauthenticated-access timeline
- 2026-05-22: initial foothold (DMZHOST ecosystem — see MITRE_CLASSIFICATION.md)
- 2026-10-03 07:16–07:21 CEST: 7 scripted root sessions from 192.76.153.253 (5–24s each)
- 2026-10-03 07:29 CEST: 1 scripted root session via Tor exit (attribution laundering)
- 2026-10-04 23:52 CEST: ROOT PASSWORD ROTATED by agent on custodian's instruction. Vector closed.

## Exposure assessment (root-readable secrets, assume exfiltrated)
- /root/evez-agentnet/.env — OpenRouter, HuggingFace, VULTR, Telegram bot token (3+ matches)
- /root/.config/himalaya/config.toml — email credentials
- /root/.openclaw/openclaw.json — gateway/model credentials
- ClawHub token + Supabase service_role (already publicly exposed — see PUBLIC_EXPOSURE_AUDIT.md)
- NOTE: all of the above were ALSO exposed in the 2026-05-22 session (filesystem enumerated).
  Treat every credential on this host as burned since 2026-05-22. ROTATION SCHEDULE REQUIRED.

## Persistence check (2026-10-04 sweep): NEGATIVE
- authorized_keys untouched since 2026-09-25 (single legit key, evezart-vmi3544756-2026-09-16)
- /etc/passwd, /etc/shadow mtime pre-incident; no new users
- no /etc/ld.so.preload, no rc.local hook, .bashrc/.profile pre-incident
- /root/.ssh/a16 (2026-10-03 23:15) = internal Hermes tooling key ("hermes-to-a16"), NOT in authorized_keys, NOT attacker persistence
- crontab/systemd: only EVEZ-owned units (see CHAIN_OF_CUSTODY.md sweep)

## New cause of action
18 U.S.C. §1030 — continuing unauthorized access, Oct 3 2026 (post-indictment-ecosystem activity).
Evidence: auth.log.copy (this directory, SHA-256 manifest), victim statement above.
