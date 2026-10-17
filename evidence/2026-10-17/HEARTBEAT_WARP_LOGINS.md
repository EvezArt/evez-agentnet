# WARP-EGRESS ROOT LOGINS — UNATTRIBUTED (raised 2026-10-17 heartbeat, needs custodian answer)

## Observed (all commands run this tick, 2026-10-17 ~00:45 UTC)
- `/var/log/auth.log`: `Accepted password for root from 104.28.157.64` — repeated short
  sessions. Oct 12 bursts 06:29–07:23 CEST (box rebooted 07:17:37 CEST, kernel
  6.8.0-142 → 6.8.0-146); Oct 15 bursts through 06:08 CEST. Last accepted login
  from ANY address: Oct 15 06:08 CEST from this IP. None since (Oct 16/17
  attackers.jsonl have zero entries for it).
- Watchdog flags (`grep UNEXPECTED_SUCCESSFUL_LOGIN evidence/2026-10-1[2-5]/attackers.jsonl`):
  Oct 12: 28, Oct 13: 32, Oct 14: 28, Oct 15: 11 → **99 flagged successful root
  logins**, all `root@104.28.157.64`. No heartbeat commit, HEALTH.md note, or
  dossier ever attributed this IP (git log grep for the IP / "warp": zero hits).
- 104.28.157.64 sits in Cloudflare WARP consumer egress space (104.28.0.0/14).
  Adjacent WARP IPs (104.28.157.65, .222) appear in Sept 28 auth.log copies with
  connection-closed (no auth success).
- Timing: bursts land 04:00–05:30 UTC = ~23:00–00:30 Iowa (CDT) — Steven's
  late-evening work window; pattern (short recurring root sessions, a supervised
  kernel upgrade + reboot on Oct 12) is consistent with EITHER the custodian on
  a WARP-routed device OR a holder of the root password.

## Verification done this tick
- No live SSH sessions now (`who`, `ss :22` empty).
- No other IP has a successful login in the window; failed-password spray
  tonight (151.56.243.21, 193.32.162.84, 128.14.232.142 — users `usuario`/root)
  is ordinary internet noise, all rejected.

## Decision point (custodian, one answer)
- IF 104.28.157.64 is the custodian's device (phone/laptop via Cloudflare WARP):
  register it in the exposure watchdog's expected list; flags stop.
- IF NOT: the root credential is compromised — rotate immediately, hunt sessions,
  re-verify the Oct 12 reboot provenance.
- No defensive action taken from the heartbeat: rotating the root password or
  blocking a possible custodian egress could lock the custodian out of his own box.
