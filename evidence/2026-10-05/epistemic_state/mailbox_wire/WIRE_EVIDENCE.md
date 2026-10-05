# Mailbox wire evidence — 2026-10-05

Primary-source Gmail artifacts pulled live from the `rubikspubes69@gmail.com`
mailbox (account `rubik69`, IMAP via himalaya) on 2026-10-05. These are the
retained RFC 5322 originals: full headers (Message-ID, Date, To, Received,
DKIM/ARC, Authentication-Results) plus complete MIME bodies and DSNs.

## Retained submissions (Sent)

| File | Sent-ID | Date | To | Message-ID | Subject (short) |
|---|---|---|---|---|---|
| r69_1218.eml | 1218 | 2026-09-19 21:31-04:00 | Cheryl.Gendron@nist.gov | `<CALr_9k3s4CdUFo2aPJ6Nn6BCNMs9VtJpQBgG+PDpBuK5A5=R5Q@mail.gmail.com>` | Self-nomination - NAIAC and NAIAC-LE (per 91 FR 45251) |
| r69_1222.eml | 1222 | 2026-09-20 05:10-07:00 | Cheryl.Gendron@nist.gov | `<CALr_9k0RnY2msasiNuDRPBu18jOnCYTH39ug4pknXRDpFUocZQ@mail.gmail.com>` | NAIAC-LE nomination follow-up |
| r69_1223.eml | 1223 | 2026-09-20 05:10-07:00 | ustechtforce@opm.gov | `<CALr_9k3Dva1VejnX2x-UXczfH9rhgGALmzC1atQr=V5rXDy2jg@mail.gmail.com>` | US Tech Force / AI security candidacy |
| r69_1224.eml | (not retained here) | 2026-09-20 05:10-07:00 | engagement@ostp.eop.gov | — | Public-interest AI governance proposal |
| r69_1225.eml | 1225 | 2026-09-20 05:18-07:00 | alicia.chambers@nist.gov, melissa.banner@nist.gov | `<CALr_9k2CBobvFhEz3LhV6P4WqJOvc+NfyLQx08XsnB5BheB8MQ@mail.gmail.com>` | Self-nomination: NAIAC + NAIAC-LE final package |
| r69_1226.eml | 1226 | 2026-09-20 05:18-07:00 | ustechtforce@opm.gov | `<CALr_9k1=3fW-hX82ZmDXC_JtwrcQYjSXf8wf_Oo9znxTJ7v8XA@mail.gmail.com>` | US Tech Force candidacy - final EVEZ submission |
| r69_1228.eml | 1228 | 2026-09-20 05:18-07:00 | alicia.chambers@nist.gov, melissa.banner@nist.gov | `<CALr_9k22+=tHSD+s0LmE0ozJwb0tfLJNSUzgymrNwoAn9-3OPg@mail.gmail.com>` | Correction: government-safe NAIAC package |
| r69_1229.eml | 1229 | 2026-09-20 05:18-07:00 | ai-inquiries@nist.gov, ai_standards@nist.gov | `<CALr_9k0R4F1ja1skwKKPE9uyCAkR0YXukNkqtw=_EN8_abo8pQ@mail.gmail.com>` | Public-interest AI governance proposal |
| r69_1230.eml | 1230 | 2026-09-20 05:18-07:00 | ustechtforce@opm.gov | `<CALr_9k0G9JjDTFKnk2oFJ0jUZSXUWyd5-k4Oh6PRrZd2vXp8Bg@mail.gmail.com>` | Correction: government-safe Tech Force package |
| r69_1232.eml | 1232 | 2026-09-21 12:39+02:00 | **naiac@nist.gov** | `<CALr_9k24JAw_wxf_V_zCtGoQym=CJoaUziP2JJ_mpB4hQDEtMQ@mail.gmail.com>` | **Self-nomination for NAIAC and NAIAC-LE, corrected government-safe package — CONTROLLING SUBMISSION** |
| r69_1234.eml | 1234 | 2026-09-21 12:48+02:00 | ustechtforce@opm.gov | `<CALr_9k3L0-9oeHVb714FdgUj6_FzNEPD8D187ODVu-r6BcV7Gw@mail.gmail.com>` | US Tech Force plain-text resend |
| r69_1233.eml | 1233 | 2026-09-21 12:42+02:00 | (self) | — | CONFIRMATION REGISTER (contemporaneous internal log; not a submission) |

## Delivery Status Notifications (DSNs, inbox)

| File | Inbox-ID | Date | Original Message-ID | Failed recipient | SMTP result |
|---|---|---|---|---|---|
| dsn_95822.eml | 95822 | 2026-09-20 05:18-07:00 | `<CALr_9k22+=...An9-3OPg@mail.gmail.com>` (= msg 1228) | melissa.banner@nist.gov | **550 5.4.1 Recipient address rejected: Access denied** (Exchange Online, LV8PEPF00000062) |
| dsn_95823.eml | 95823 | 2026-09-20 05:18-07:00 | `<CALr_9k0G9Jj...rZd2vXp8Bg@mail.gmail.com>` (= msg 1230) | **ustechtforce@opm.gov** | **550 5.4.1 Recipient address rejected: Access denied** (Exchange Online, BN7PEPF0000009B) |
| dsn_95921.eml | 95921 | 2026-09-21 03:48-07:00 | `<CALr_9k3L0-9...r6BcV7Gw@mail.gmail.com>` (= msg 1234) | **ustechtforce@opm.gov** | **550 5.4.1 Recipient address rejected: Access denied** (Exchange Online, BN7PEPF00000099) |
| dsn_96050.eml | 96050 | 2026-09-21 20:13-07:00 | (comments@whitehouse.gov thread) | comments@whitehouse.gov | Delay: recipient server connect timeouts (Gmail retrying) |
| dsn_96172.eml | 96172 | 2026-09-22 22:29-07:00 | (comments@whitehouse.gov thread) | comments@whitehouse.gov | Failure: connect timeouts after full retry window |

## Findings the wire establishes

1. **NAIAC controlling submission (msg 1232 → naiac@nist.gov) has NO bounce in
   the retained mailbox.** As of 2026-10-05 there is no DSN, no rejection, and
   no reply from any nist.gov sender in the inbox. Absence of a bounce is
   consistent with delivery; it is not proof of receipt or review.
2. **Every send to `ustechtforce@opm.gov` FAILED** — messages 1223, 1226,
   1230 (attachments), and 1234 (plain text) all to that exact address; DSNs
   retained for 1230 and 1234 (550 5.4.1 Access denied, Exchange Online).
   The address `ustechtforce@opm.gov` contains a doubled t; current official
   OPM/Tech Force address is `ustechforce@opm.gov`. Therefore:
   **no US Tech Force submission of any kind has ever been delivered.**
   Prior status of "submitted" for Tech Force is corrected to
   **UNDELIVERED (typo address, SMTP 550)**.
3. One liaison copy (msg 1228 → melissa.banner@nist.gov) also bounced 550
   (the alicia.chambers@nist.gov recipient of the same message produced no
   DSN; per-recipient partial delivery is not distinguishable from these
   artifacts alone).
4. The two confirmation-register claims that "ustechtforce@opm.gov verified
   via techforce.gov" and "message IDs verified" are now contradicted by the
   retained DSNs. The register's own caveat — "Sent status is not agency
   acknowledgment" — is the controlling statement.
5. Comments@whitehouse.gov submissions suffered transport-level connect
   timeouts (whitehouse.gov MX not accepting Gmail connections in that
   window), eventually recorded as failed.

## State transitions driven by this evidence

- NAIAC: **SUBMITTED_DELIVERED** wire-proven to naiac@nist.gov (no DSN);
  agency receipt/review UNKNOWN.
- US Tech Force: **UNDELIVERED** — SMTP 550 on every attempt; no candidacy
  ever reached OPM. Correct-address resend is the open action.
- White House comments: transport failed (timeout, then failure DSN); no
  evidence the webform channel failed — the webform confirmation of
  2026-09-19 is a separate channel and is unaffected by these DSNs.

## Provenance

- Exported 2026-10-05 via `himalaya --account rubik69 message read -m Sent <ID> --raw`
  (Sent) and `message read <ID> --raw` (inbox DSNs), IMAP over TLS.
- SHA-256 of each artifact recorded in SHA256SUMS.txt in this directory.
- The mailbox is live; artifacts are retained originals, not reconstructions.

## Institutional receipts (rubikspubes69 inbox) — added 2026-10-05 (second pull)

| File | Date | From | Verdict |
|---|---|---|---|
| inst_95747.eml | 2026-09-20 01:06Z | Wyoming Highway Patrol Public Records (messages@nextrequest.com, dkim=pass) | Request #26-4120 SUBMITTED |
| inst_97226.eml | 2026-09-28 23:29Z | Wyoming Highway Patrol Public Records (dkim=pass) | **Request #26-4120 CLOSED — "All records have been released, and your request has been fulfilled."** Full-ladder institutional state: number -> reply -> documents released. |
| inst_96069.eml | 2026-09-22 10:25Z | efoia@subscriptions.fbi.gov (dkim=pass, spf=pass) | **eFOIA Request Received** — FBI's own mail system, addressed to Steven Vearl Crawford-Maggard, full submission record |
| inst_96065.eml | 2026-09-22 10:12Z | efoia@subscriptions.fbi.gov | eFOIPA Authorization Request notice |
| inst_97912.eml | 2026-10-01 14:14Z | efoia@subscriptions.fbi.gov (dkim=pass) | **eFOIA files available** — download links + access token (retained; token not reproduced here) |

## Security signals observed during the pull (fiersteity inbox) — LIVE

| File | Date | What |
|---|---|---|
| gsignup_3199.eml (+4 copies) | 2026-10-05 06:44-07:00 | Google Payments: "Someone used your account to try to sign up for Google Cloud. Google denied the signup attempt" — FIVE attempts in ~16 minutes |
| sec_2932.eml | 2026-10-04 03:56Z | App password created for fiersteity@gmail.com "for Hermes" |
| sec_2914.eml | 2026-10-02 01:01Z | Base44 granted access to Google Account data |

The "billing.admin request on billingAccounts/010E59-DF9212-C44DB2 with
message 'Favors for my admin'" was NOT found in any connected mailbox
(inbox, All Mail, Spam, Trash searched on fiersteity, rubik69, rubik70 for
"Favors", "admin", "troubleshooter", "billingAccounts", "IAM"). The billing
account 010E59-DF9212-C44DB2 history IS in fiersteity (suspended 2026-07,
terminated 2026-08-06). If that notification arrived, it landed in a
mailbox not connected to this environment, or in a Google Cloud console
channel. Steven's direct confirmation is required before treating it as
hostile or legitimate.

## DSN-to-original mapping (verified by Message-ID)

- dsn_95822 (550 Access denied, melissa.banner@nist.gov) -> msg 1228
  (`CALr_9k22+=...An9-3OPg`) — liaison copy; the alicia.chambers recipient
  of the same message has no DSN.
- dsn_95823 (550 Access denied, ustechtforce@opm.gov) -> msg 1230
  (`CALr_9k0G9Jj...rZd2vXp8Bg`) — corrected Tech Force package.
- dsn_95921 (550 Access denied, ustechtforce@opm.gov) -> msg 1234
  (`CALr_9k3L0-9...r6BcV7Gw`) — plain-text resend. This is the send whose
  own body said attachments were "rejected by OPM mail filtering"; the wire
  says the address itself was rejected with 550 Access denied — the mailbox
  never accepted it at all, so no filtering verdict on content exists.
- dsn_96050 (delay) / dsn_96172 (failure) -> comments@whitehouse.gov thread,
  connect timeouts at whitehouse.gov MX.

## Contested claim: "Sept 20 correct-address send to ustechforce@opm.gov"

The external audit (ChatGPT pull) reports a Sept 20 transmission to the
CORRECT address ustechforce@opm.gov (Message-ID `CALr_9k0K8T...`, "AI Czar /
AI Force application"). No such message is retained in any of the three
connected mailboxes: every retained Tech Force send (1223, 1226, 1230,
1234) is addressed to the TYPO ustechtforce@opm.gov, and the AI Czar/AI
Force messages retained in rubik70 (Sent 607-609, 2026-09-19) and rubik69
(msg 1215-1217) predate that claimed send. Either it lives in a mailbox
not connected here, or it does not exist. Until its artifact is produced,
Tech Force stays UNDELIVERED with the typo-address DSNs as the only wire
facts. The same audit's USAJOBS Talent Network claim (joined 2026-09-21) is
a portal state, not a mailbox artifact — portal access would be needed to
verify it; rubik69 Sent msg 1235 references the Talent Network join.
