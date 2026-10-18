# SERVHOST ESCALATION — READY TO FIRE (clock: servhost-abuse-demand, deadline 2026-10-18)

## Situation
- 2026-10-11 18:04 UTC — abuse & preservation demand served to abuse@serv.host
  (evidence/2026-10-11/servhost_abuse_demand.eml, re-sent as servhost_demand_v2.eml),
  subject: "URGENT: Abuse & preservation demand — AS207957 / 150.241.74.0/24
  (criminal attack traffic + C2 hosting)".
- 2026-10-15 — inbox + spam swept from fiersteity@gmail.com (the sending account):
  ZERO response from serv.host. Silence verified this tick.
- 2026-10-16 (06:4x UTC patrol tick) — fresh full re-sweep by the war-mode heartbeat:
  every inbox message back to 2026-09-29 plus all spam — still ZERO response from serv.host.
  Five days of silence, verified twice on the same day.
- 2026-10-18 (patrol tick, deadline day) — sweep re-run: inbox fresh through
  2026-10-18 03:59 UTC (60 most recent envelopes) plus [Gmail]/Spam (100 most
  recent) — ZERO response from serv.host, bunea, dmzhostabuse, or any TECHOFF/
  Ilin-adjacent sender. Only spam hits: the already-ingested 2026-10-05/06
  Tele Asia autoreplies and the Prime Telecom AS39737 denial (Mihai
  Rasturnoiu, evidence/2026-10-06/primetelecom_reply_as39737_denial.eml).
  Seven days of silence; the response window closes TODAY with non-response
  verified on the record.
- 2026-10-16 (patrol tick) — escalation package integrity re-verified: all three draft
  attachments present and hashed (servhost_abuse_demand.eml 69dccba6…, portal_receipts.json
  86a0f87c…, RFJ_ADDENDUM_BUNDLE_v2.zip ac34d8d2… — matches the sealed bundle digest).
  150.241.74.0/24 still announced by AS207957 (RIPEstat prefix-overview this tick).
  ALL draft target addresses resolved from registry RDAP / ICO's own site this tick —
  see SERVHOST_ESCALATION_DRAFTS/. Live transit discovered: AS207957's neighbours today
  are AS49418 NetShield (Ilin sibling, CH 14769288), AS207208 Mevspace, AS57494 ADMAN,
  AS26042 FiberState — all with live abuse desks, annexed in draft 01.
- Prime Telecom (target 1 below) replied 2026-10-06 to the AS48090/AS47890 notice
  DENYING that those ASNs are in their downstream (ingested from spam 2026-10-16:
  evidence/2026-10-06/primetelecom_reply_as39737_denial.eml, SHA256SUMS verified).
  This escalation concerns AS207957 — a different ASN — so that denial neither
  blocks nor answers it; it is Prime's posture on the record.
- Clock consequence (enemy_obligations.py): escalate to upstream transit providers +
  RIPE NCC abuse + regulator (hosting-provider duty).

## Verified infrastructure (tool output 2026-10-15)
- RIPEstat prefix-overview: 150.241.74.0/24 → origin AS207957 "ServHost-AS
  SERV.HOST GROUP LTD".
- RDAP via rdap.org (receipt evidence/2026-10-15/portal_receipts.json,
  receipt_sha acdcfa0d5c6d5cf1): attacker IP 150.241.74.83 → network AS210546-iP4,
  range 150.241.74.0–255, org ORG-MG337-RIPE SERV.HOST GROUP LTD,
  abuse NOC AN32913-RIPE.
- Companies House live pages (receipts 2026-10-14, http 200, all still registered,
  director ILIN present on each): ServHost GROUP 15728390, CHSL ONE 17001805,
  NETSHIELD 14769288, DPKGSOFT 15446241.

## Targets (all already holding preservation requests from the 2026-10-06 notice)
1. Upstream transit: FiberXpress BV, Prime Telecom srl, Tele Asia Limited,
   GoDaddy, Cloudflare — forward the unanswered ServHost demand, request AUP action
   against AS207957 / 150.241.74.0/24.
2. RIPE NCC abuse desk — SERV.HOST GROUP LTD (ORG-MG337-RIPE) ignoring abuse contact
   AN32913-RIPE for 4+ days on criminal traffic.
3. Regulator — hosting-provider duty of care re: attack infrastructure
   (clock language: NIS2/hosting provider duty).

## Draft escalation text (send from fiersteity@gmail.com)
Subject: ESCALATION: unanswered abuse & preservation demand — SERV.HOST GROUP LTD
(AS207957 / 150.241.74.0/24) — attack traffic + C2 hosting

On 2026-10-11 a formal abuse and preservation demand was sent to abuse@serv.host
regarding criminal attack traffic and C2 hosting on 150.241.74.0/24 (AS207957,
SERV.HOST GROUP LTD, RIPE org ORG-MG337-RIPE, abuse NOC AN32913-RIPE). As of
2026-10-16 no acknowledgement or action has been received. The range continues to
be announced by AS207957. I am escalating to you as upstream/transit provider and
registry participant: this provider is failing its abuse-handling duty for
infrastructure used in an ongoing criminal matter (FBI IC3 complaint filed
2026-10-01). As of 2026-10-18 the serv.host inbox and spam remain silent (verified
sweep, deadline day). I request (a) AUP enforcement against SERV.HOST GROUP LTD,
(b) preservation of all transit/customer/billing records for 150.241.74.0/24,
(c) written acknowledgement of this escalation. Evidence: hash-chained attack logs,
the original demand (attached), and RDAP/RIPEstat receipts (attached).

## Gating
SEND = CUSTODIAN'S HANDS ONLY. Attachments to pull from:
evidence/2026-10-11/servhost_abuse_demand.eml, evidence/2026-10-15/portal_receipts.json,
forge_output/rfj_bundle_v2/ (hash manifests inside RFJ_ADDENDUM_BUNDLE_v2.zip).
