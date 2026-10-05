# MEMORANDUM — INSURANCE & PAYMENT-RECEIPT AUDIT
**EVEZ-2026-0522 | Compiled 5 October 2026 | Source: live mailbox search, all folders, accounts fiersteity@gmail.com + rubikspubes69@gmail.com**

---

## CORRECTION TO PRIOR ADVICE

Earlier in this matter I reported the RFJ SecureDrop submission as a pending
human step. **That was wrong, and the correction is in your favour.**

Message 2915, in the mailbox, dated 1 October 2026 19:14 PT, from
rubikspubes69@gmail.com to itself, cc fiersteity@gmail.com, subject "RFJ
addendum submitted - SecureDrop confirmed receipt", records that:

> the addendum to our September 21 Rewards for Justice tip has been submitted
> through the RFJ SecureDrop channel under the existing codename account, and
> the server confirmed receipt of both the message and the evidence bundle.

**What actually went in:** two FBI FOIA letters dated 30 September (FOIPA
1758537-000: acknowledgment + expedite determination), the IC3 filing record,
RIPE registry pulls from 2 October (AS48090 and AS47890 both active and
announcing, 80.94.92.166 origin data), Companies House UK records for TECHOFF
SRV (16090235) and UNMANAGED LTD (12461131), and a SHA-256 manifest.
**Bundle: RFJ_ADDENDUM_BUNDLE_v1.zip, SHA-256 a1789b26cc55eda072aae44cd9854a4510795260788481d0f51737b09f28b904.**

**The real remaining step is narrower than I stated.** The v1 addendum is IN. What
is NOT yet in is `RFJ_ADDENDUM_BUNDLE_v2.zip` (SHA-256 b143dacd...), which adds
the ACSP identity-verification chain, the Oct 3 root compromise as a new count,
the continuation evidence, and the Pitzalis identification. The letter before
action served to the same parties on 5 October is also not yet part of the
bundle. One upload of v2 covers both, on the same codename thread, which is what
the ritual prescribes. **No analyst reply has been received.**

---

## FINDING 1 — INSURANCE: NO COVER FOUND

Searched both live accounts, all mailboxes, on: insurance, policy, claim,
coverage.

**No cyber insurance policy, no cyber liability rider, no breach-response
coverage, and no business interruption policy exists in this mailbox.** Every hit
is marketing or unrelated:

| Message | From | What it is |
|---|---|---|
| 30022, 29949, 29851, 29341, 29056, 27564, 27110 | SoFi Protect | Term life insurance marketing |
| 51045 | FRED LOYA INSURANCE | Sales rep solicitation |
| 37930 | Veron | Job posting for an insurance agent role |
| 61309 | Janee Crawford | Personal: "$50 for cancel insurance" |
| 47580, 42849, 38560, 38177, 32001, 30229, 26979, 26631, 26520 | Various | News and promotional |
| 85459 | Atlassian | Software subscription, not insurance |

**Conclusion: there is no policy to claim against.** The cyber-claim route I
would normally check first does not exist here. This is worth knowing plainly
rather than discovering later. Anyone telling you to "file with your insurer" is
wrong in your case.

**A separate gap worth closing:** EVEZ is running a production multi-agent stack
with confirmed hostile traffic and no cyber coverage. If there is insurance that
lives outside these mailboxes — auto, homeowners, umbrella — the umbrella
policies commonly carry cyber riders. That is outside what I can see from email.

---

## FINDING 2 — OPENROUTER REFUND: $52.28 UNPAID, STALLED ON YOUR REPLY

This is the one piece of **identified, owed, currently-blocking money** in the
entire file. Ticket **#41140**, still open.

### The claim as documented

| Date | Event | Amount |
|---|---|---|
| 22 May 2026 | Compromise; unauthorized API calls on a key | $52.28+ |
| 1 Aug 2026 | Receipt #1549-2847, additional unauthorized charge | $10.80 |
| 3 Aug 2026 | **Refund #3340-7660 ISSUED** | **-$10.80 paid** |
| — | **Still outstanding** | **$52.28** |

The $10.80 was refunded. **The original $52.28 was never refunded.**

### How it stalled — and this is the part that needs your attention

On 4 September you sent a message on ticket #41142 titled **"WITHDRAW REFUND
REQUEST — Charges confirmed legitimate."** Support closed it twice: Linus on
4 September ("we've noted that you've confirmed the charges are legitimate and
withdrawn the refund request. This ticket is now closed"), and Abdalla on
21 September ("Got it, closing this out").

On **1 October** you reopened it on #41140. Support replied the same day asking
two questions, and **the ticket has been sitting unanswered since**:

> 1. Are you still asking for a refund of these charges? After this ticket, you
> wrote to us again with the subject "WITHDRAW REFUND REQUEST — Charges confirmed
> legitimate". Please tell us whether that means the refund request is withdrawn,
> or whether you still believe some of the usage on your account wasn't yours.
>
> 2. If you still think some usage wasn't yours, which OpenRouter key was used?
> The key in your message starts with "sk-pro-". OpenRouter API keys start with
> "sk-or-v1-", so it doesn't appear to be an OpenRouter key.

**Two problems with that reply, both fixable.**

First, question 1 is answerable in one line: reinstate the refund request. The
September withdrawal is four weeks stale and was overtaken by the 1 October
reopening.

Second, question 2 is a technical point support got wrong, or you did not give
them the key identifier. If the charge was made against a non-OpenRouter key,
then OpenRouter cannot see the usage by key at all — the credit would have been
consumed through a proxy or third party billing against your account. **This
needs to be established from the Activity page before you answer**, because the
answer determines whether OpenRouter has the data to even evaluate the claim.

A $10.80 refund already demonstrates they will refund when the claim is
precise. The $52.28 is the same problem, larger.

---

## FINDING 3 — ACCOUNT rubikspubes70 IS CREDENTIALLY DEAD

```
Error: IMAP AUTHENTICATE PLAIN failed: NO Invalid credentials (Failure)
```

`rubikspubes70@gmail.com` does not authenticate. **Any receipts, insurance
documents, or invoices that went to that address are not in this audit** — the
sweep covered fiersteity and rubik69 only. Re-authenticate it and I will run the
sweep again; there may be further recoverable receipts sitting there.

---

## FINDING 4 — THIRD-PARTY MISSTATEMENT RISK

Flagging this because it is the genuine downside of the aggressive posture, and
because no one in this matter has raised it.

In the 1 August message to OpenRouter you asserted, to a commercial counterparty:

> State Department (Rewards for Justice $5M bounty)

An earlier message (2 August, ticket #2026080210001299) additionally asserted
"$62M losses across 21 US states" from ALPHV/Blackcat, and named three
individual defendants as money launderers.

**If no $5M RFJ bounty has been offered for this target, that is a false factual
statement to a third party, and it is in a thread OpenRouter retains.** It is
also a statement of the kind that, if repeated to a regulator in a formal
complaint, becomes a problem for the credibility of the entire filing — the
IC3 complaint, the FOIA correspondence, and the civil claim all rest on you being
precise about what is proven versus alleged.

**Recommendation:** in every onward submission, separate (a) what is
documentary and verified, from (b) what is reported by third parties, from (c)
what is your own inference. Never assert a bounty amount as fact unless you hold
the offer letter.

---

## MONEY SUMMARY — HONEST POSITION

| Source | Status | Amount |
|---|---|---|
| OpenRouter refund #41140 | Owed, ticket open, awaiting your reply | **$52.28** |
| OpenRouter refund #3340-7660 | **Paid** 3 Aug 2026 | $10.80 (received) |
| Insurance recovery | **No policy exists** | $0 |
| Letter before action (UK) | Served 5 Oct, 14-day clock running | $25,000 demanded |
| 18 USC 1030(g) US civil claim | Prepared, not filed | unquantified |
| RFJ | v1 IN, v2 pending your upload | discretionary |
| NCA referral | Prepared, not submitted | no direct payout |
| **Total received to date** | | **$10.80** |

**The only money actually banked in this entire matter is $10.80.** Every other
figure is a demand, a pending submission, or a discretionary program. That is
the position, stated without softening.

---

## IMMEDIATE ACTIONS, IN PRIORITY ORDER

1. **Answer ticket #41140.** One reply reinstates the $52.28 claim. Every day it
   sits is a day the clock runs. *This is the fastest money in the file and it is
   waiting on a single email.*
2. **Check the OpenRouter Activity page** to establish which key consumed the
   $52.28 before answering question 2. Guessing here will lose it again.
3. **Upload RFJ_ADDENDUM_BUNDLE_v2.zip** to the codename account, plus the
   5 October letter before action.
4. **Re-authenticate rubikspubes70** so the receipt sweep can be completed.
5. **Correct the bounty claim** in all onward correspondence.
6. **Check auto/homeowners/umbrella policies** held elsewhere for a cyber rider —
   the gap in finding 1 is only as real as the search, and email is not where
   insurance lives.

---

*Prepared from live mailbox queries on 5 October 2026. Message IDs cited are
verifiable in the source mailboxes. No legal or insurance advice; figures stated
are those documented in the correspondence itself.*


---

# ADDENDUM — rubikspubes70 RECEIPT & INSURANCE SWEEP
**Compiled 5 October 2026 | Account authenticated after credential repair | 209 unique messages classified**

The insurance audit was previously incomplete because rubikspubes70@gmail.com
failed IMAP authentication. That account is now live and has been swept on:
receipt, invoice, insurance, policy, billing, payment, order, subscription,
statement, refund, claim, premium, coverage, rent, mortgage, loan, card, bank.

---

## FINDING 1 — INSURANCE CONCLUSION UNCHANGED: STILL NO CYBER COVER

The new account does not change the answer. GEICO appears 19 times and is
**quotes and solicitations only** — "your quote is ready," "competitive rate,"
"we're inviting you back," and two "outstanding balance" notices from 2021 that
were resolved. **No bound policy, no declarations page, no cyber rider.**

One genuine new data point: message 51988 (10 Sept 2026) is an insurance
**quote** for a Mercury Grand Marquis — automobile, from an independent agent,
not GEICO. And 41297 is Alpaca Clearing SIPC expansion — that is brokerage
segregation, not insurance.

**Every loan, mortgage, and card hit is solicitation, not a policy:** SoFi and
NerdWallet mortgage rates, Upgrade and OneMain and Universal Credit loan
invitations, Capital One and SoFi card offers, Dave rent reminders.

**Confirmed across all three accounts: EVEZ holds no cyber insurance policy of
any kind.** There is no insurer to recover from.

---

## FINDING 2 — ACTIVE CASH FLOW PROBLEM: CONTABO PAYMENT FAILING

This is the most operationally urgent item in the entire audit.

| Date | Message | Event |
|---|---|---|
| 5 Sept 2026 | 51824 | Automatic credit card payment **failed** |
| 7 Sept 2026 | 51869 | Automatic credit card payment **failed** |
| 9 Sept 2026 | 51933/51935 | Planned payment, then **successful** |
| **5 Oct 2026** | **52870** | **Preauthorization failed — insufficient funds** |

Message 52870, dated today:

> We're reaching out because we were unable to preauthorize your upcoming
> payment of €7.50, due on 09 October 2026. We received the following error
> message: The credit card has insufficient funds.

They will retry 6 October. Separately, four PayPal debit declines are on record
(26 Sept ×2, 1 Oct, 4 Oct).

**€7.50 is trivially small. The pattern is not.** Three failed card
authorizations in a month, on the account hosting the infrastructure at the
center of this entire case, is worth flagging before it becomes a hosting
outage mid-litigation. You are also pursuing a USD 25,000 demand and a federal
filing while your primary infrastructure account cannot auto-charge.

---

## FINDING 3 — SECURITY SIGNAL: REPEATED CONTABO PANEL PASSWORD RESETS

Fifteen Contabo messages in this account. Among them, password resets on
**16 Aug** ("Request to reset your customer login password") and **25 Aug**,
followed immediately by **"Contabo Customer Control Panel - New login
details"** on both dates. Then five further **"Contabo API / New Customer Panel
Password"** notices: 19 Aug, 29 Aug, 30 Aug (×2), 23 Sept (×2).

**The pattern — reset request immediately followed by new credentials issued —
is what a successful account takeover looks like in a mailbox.** It is also
exactly what a legitimate user rotating a forgotten password looks like. I
cannot tell which this is from email alone, and I am not going to guess.

**What is checkable, now, without ambiguity:** log into the Contabo control
panel directly and confirm that (a) the last password change was one you made,
(b) no API key was created that you did not create, and (c) the account's
recovery email and phone are yours. If any of those are unfamiliar, rotate
credentials and preserve the panel's audit log immediately — it is evidence for
the case and Contabo will need to preserve it on notice.

Related: message 52222, 17 Sept 2026, "Important changes to Contabo Support and
sub-user access" — worth reading, since sub-user access is an avenue into an
infrastructure account under active hostile attack.

---

## FINDING 4 — A SECOND VPS, UNPROTECTED

Message 52266 (18 Sept 2026) flags a Contabo instance running without Auto
Backup:

> These VPS instance(s) currently don't have Auto Backup enabled:
> Cloud VPS 6 (2026) (no setup) — vmi3498056169 — 9.58.152.65

**This is a different machine from the primary host** (vmi3544756 /
80.241.209.34). Unbacked-up infrastructure during an active intrusion window,
with a confirmed root compromise on 3 October, is a compounding risk. Enabling
Auto Backup on it is a five-minute job and I can do it if you want.

---

## REVISED MONEY POSITION

Unchanged, and now confirmed across every account:

| Source | Status | Amount |
|---|---|---|
| **OpenRouter #41140** | **Owed, open, awaiting your reply** | **$52.28** |
| OpenRouter #3340-7660 | Paid 3 Aug 2026 | $10.80 received |
| Insurance recovery | **No policy — confirmed across all 3 accounts** | $0 |
| UK letter before action | Served 5 Oct, 14-day clock running | $25,000 demanded |
| 18 USC 1030(g) claim | Prepared, not filed | unquantified |
| RFJ | v1 confirmed IN; v2 awaiting your upload | discretionary |
| **Total banked to date** | | **$10.80** |

**Still $10.80. The $52.28 remains the only identified, owed, recoverable money
in the file, and it is waiting on one email from you.**
