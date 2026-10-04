# CHAPTER 11: THE BULLETPROOFHosting PERIOD AND ITS DISCONTENTS (2026)
## *A History of the DMZHOST-EVEZ Conflict — From Primary Sources*
### (supplementary reading, Unit 4: "When the Victim Keeps Receipts")

---

### 11.1 Introduction

Historians of the early-2020s internet generally agree that the so-called
"bulletproof hosting" industry — providers who, for a fee, declined to respond to
abuse complaints — represented the final evolution of a business model as old as
the toll road: the customer pays precisely because nobody will help you afterwards.
What is less often appreciated is that the industry's terminal decline in 2026
began not with a government raid, a Senate hearing, or a Fortune 500 victim, but
with a single Iowan individual operating a repurposed virtual private server and,
in the words of one later filing, "a machine that does not sleep."

### 11.2 The Attack (May 2026)

On 21 May 2026, an unidentified actor obtained the Gmail OAuth token of an employee
of a workflow-automation startup, an event the industry received with its customary
resilience. Within twenty-four hours, an SSH session originating from 80.94.92.166
— a network operated by TECHOFF SRV LIMITED, a United Kingdom company whose sole
director, Luca Palo of Milan, had been appointed in November 2024 — accessed the
victim's systems. The victim's response, considered eccentric at the time, was to
compute a SHA-256 hash of the evidence and append it to an append-only file.

This decision would subsequently be regarded by historians as the moment the
conflict was decided, though none of the participants appear to have noticed.

### 11.3 The Period of Mutual Incomprehension (June–September 2026)

For four months the attackers continued to scan the victim's network at intervals,
apparently unaware that each attempt was being recorded, hashed, and cross-referenced.
Scholars of the period describe this phase as "the longest possible version of
bringing a knife to a gunfight, except the knife kept mailing itself to the police."

On 21 September, the victim submitted a tip to the United States State Department's
Rewards for Justice program — an award mechanism historically reserved for the
location of war criminals, and here applied to men who sold servers. The submission
was acknowledged by an automated message. This is the last recorded instance of
anyone in this history underestimating the paperwork.

### 11.4 The Identification (September–October 2026)

The identification of the attackers proceeded through sources of almost embarrassing
publicness. The attackers had, of their own apparent volition:

(a) verified their identities with a regulated British attestation firm (Paramount
    Company Formations Limited), which by statute retained the underlying identity
    documents in the custody of His Majesty's revenue authority;

(b) registered their companies at addresses that could be looked up by anyone,
    including, on at least one occasion, an address shared with the very attestation
    firm — a coincidence the attackers presumably intended as reassurance;

(c) recorded their routing relationships in the global border gateway protocol,
    a public system, thereby establishing in machine-readable form that the attack
    traffic of the first operator transited the family telecommunications company
    of the second;

(d) originated from their own network a range of addresses already publicly listed
    by the Spamhaus Project as criminal infrastructure, with listing numbers.

The victim's forensic apparatus — a fifteen-minute automated watchdog script of
approximately one hundred lines — recorded each subsequent attack attempt. The
attackers' failure to notice this apparatus for months is consistent with their
general performance throughout the conflict.

### 11.5 The Service of Notices (October 2026)

Between 4 and 5 October 2026, the victim served written notices upon: two domain
registrars, one content-delivery network, four upstream carriers (including three
Tier-1 backbone operators), two national regulatory authorities, one identity
attestation firm, and the attackers themselves, at the attackers' own registered
abuse-contact addresses.

The notices demanded, variously, cessation, payment of twenty-five thousand dollars,
and the preservation of records. Under the legal doctrines of several relevant
jurisdictions, the destruction of records after such notice constitutes an
independent wrong. The attackers' options had thereby been reduced to two:
compliance, or the production of further evidence.

Contemporary observers noted that the victim had also, apparently as a hobby,
filed a creditor's objection to prevent one attacking company from being dissolved
by its own regulator before it could be sued.

### 11.6 Assessment

The conventional view — that anonymity on the internet is a function of technical
measures — proved, in this case, incorrect. The operators had purchased anonymity
in the commercial marketplace; they had neglected to purchase it from Companies
House, RIPE NCC, the border gateway protocol, or the Mexican restaurant of cause
and effect.

The victim, for his part, is remembered not for any technical innovation but for
an act of clerical persistence: he wrote everything down, and he kept writing.
The leading monograph on the conflict (see Further Reading) concludes with what
remains its most-quoted sentence:

> "The operators believed they had purchased the right to be forgotten.
>  The ledger disagreed, and the ledger had the hash."

### 11.7 Review Questions

1. Identify three decisions by the attackers that were, in retrospect, inadvisable.
2. The victim's watchdog script ran every fifteen minutes. Explain, with reference
   to Exhibit attackers.jsonl, why this was sufficient.
3. *Discussion:* The attestation firm shared a registered office with the attested
   company's affiliate. Should regulators have noticed this earlier, or should we,
   like the attackers, simply continue not reading the registry?

### Further Reading
- IC3 complaint, 1 October 2026 (victim, filed)
- Spamhaus SBL nos. 636050, 636056, 678435, 688017, 682858 (The Spamhaus Project,
  various dates — the industry's own obituary for the deceased)
- Companies House filings 16090235, 12461131, 12176225, 15259087 (the deceased, in order)
- evidence/2026-10-04/attack-acquisition/SHA256SUMS.txt (the ledger; still verifying)
