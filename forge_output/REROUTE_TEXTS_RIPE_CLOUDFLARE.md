# REROUTE TEXTS — RIPE NCC + CLOUDFLARE (dead-mailbox replacements)

Prepared 2026-10-20. Both prior channels proved dead: RIPE NCC Support (ticket #1124364, 19 Oct) confirms abuse@ripe.net is unmonitored; Cloudflare's abuse@ auto-replied "This email address is not monitored." Both live channels are web forms. Submission = custodian's hands, or his explicit GO for a browser-driven submit.

## 1. RIPE NCC — reporting-procedure form
**Where:** https://www.ripe.net/about-us/support/contact/reporting-procedure/ — category **"Incorrect contact information in the RIPE Database"** (precondition "already tried to contact the maintainer" is satisfied: three addresses, 11 Oct, all machine-rejected). Backup category: "Violation of RIPE Policies and RIPE NCC Procedures" (RIPE-705 requires a working abuse-mailbox; the NCC validates annually and follows up where incorrect).

**Body (paste):**

Subject: Non-operational abuse-mailbox for ORG-MG337-RIPE / AS207957 (150.241.74.0/24) — request validation per RIPE-705

The abuse-mailbox published for this resource is non-operational:

- Resource: inetnum 150.241.74.0 - 150.241.74.255 (netname AS210546-iPv4, mnt-by SERVHOST-MNT), announced by AS207957 (SERV.HOST GROUP LTD, ORG-MG337-RIPE); abuse contact per RDAP: abuse@serv.host.
- 11 October 2026, 18:06 UTC: our written preservation demand was rejected on all three standard addresses — abuse@serv.host, noc@serv.host, postmaster@serv.host — with SMTP 554 5.7.1 "Message rejected under suspicion of SPAM". Delivery-status notifications are preserved and hashed (abuse b6c6dd04…, postmaster ec735dfe…, noc a8710ff0…).
- Re-service on 11 October has gone unanswered as of 20 October.
- This range attacked our systems on 8 October 2026 (logged and mitigated) and is documented in third-party threat intelligence (hexastrike TLP:CLEAR, April 2026) as SmartLoader→StealC exfiltration command-and-control, including a blockchain dead-drop resolver.
- RIPE NCC Support (ticket #1124364, 19 October 2026) confirmed abuse@ripe.net is not monitored and directed us to the responsible network's abuse contact — the non-operational mailbox reported here.

RIPE-705 requires abuse-mailbox attributes to be available in an unrestricted way and states the RIPE NCC validates them, following up where incorrect. Request: validation of this abuse-mailbox and member follow-up to restore a working abuse contact.

Contact: Steven Crawford-Maggard, rubikspubes69@gmail.com

## 2. Cloudflare — abuse form
**Where:** https://abuse.cloudflare.com/ in a browser (the form 403s non-browser clients — that's fine, it is browser-submitted by design). Category: closest to malware/C2 hosting. The form wants a URL — **[VERIFY at submit: which ServHost-associated domain actually resolves behind Cloudflare; use the domain you preserved against on 5 Oct]**.

**Report text (paste):**

Cloudflare services front domains associated with SERV.HOST GROUP LTD (UK company 15728390; AS207957), whose announced address space (150.241.74.0/24) hosts malware command-and-control infrastructure and originates attack traffic:

- The range is documented in third-party threat intelligence (hexastrike TLP:CLEAR, April 2026) as SmartLoader→StealC exfiltration C2, including a Polygon-contract dead-drop resolver (IOC SHA256 87de3e5a…).
- The range attacked my systems on 8 October 2026 (logged, mitigated at firewall).
- The operator's published abuse contact machine-rejects all mail (SMTP 554 5.7.1 on abuse@/noc@/postmaster@serv.host, 11 October 2026; DSNs preserved and hashed) and has ignored re-service since.
- A preservation demand was served on Cloudflare 5 October 2026 and remains unanswered; your abuse@ address auto-replied "not monitored" on 19 October 2026.

Requested: AUP review of the associated domain(s)/account and preservation of relevant records.

Contact: Steven Crawford-Maggard, rubikspubes69@gmail.com
