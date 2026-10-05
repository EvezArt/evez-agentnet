# PARTICULS OF CLAIM — HIGH COURT OF JUSTICE, BUSINESS AND PROPERTY COURTS
## Claim No: [    ]    (to be assigned on issue)

**BETWEEN:**

**CRAWFORD-MAGGARD** *(Claimant)*
- 66226 N Agua Dulce Dr, Desert Hot Springs, CA 92240, USA
- rubikspubes69@gmail.com

**and**

1. **PALO**, Luca *(First Defendant)* — trading/acting via TECHOFF SRV LIMITED (CRN 016090235), 8 Via Leonardo Bistolfi, Milano, Italy 20134; also director of BESTDC LIMITED (15259087)
2. **BUNEA**, Petru-Octavian *(Second Defendant)* — UNMANAGED LTD, 14-16 Timisoara, Romania; d/b/a BUNEA TELECOM SRL
3. **DMZHOST.CO** *(Third Defendant)* — corporate/hosting entity operating the infrastructure described at paragraph 6

**CLAIMANTS:** Trespass to chattels; conversion; breach of the implicit duty of a
network operator to maintain reasonable security; misuse of private information;
unjust enrichment. Civil cause of action arising under s.1030(g) of the
Computer Fraud and Abuse Act 18 U.S.C. §1030(g) (private right of action).

---

## 1. THE CLAIMANT
1.1 The Claimant is a United States sole proprietor resident in California, operating
an autonomous multi-agent compute estate (the "**Estate**") on leased VPS capacity
within the United Kingdom (Contabo VPS `vmi3544756`, public address 80.241.209.34,
Tailnet `100.126.180.47`).

## 2. THE DEFENDANTS
2.1 The First Defendant is the natural person identified in corporate registry records
as director of TECHOFF SRV LIMITED and BESTDC LIMITED.
2.2 The Second Defendant is the natural person identified in RIPE registration records
(ripe_AS48090.txt, ripe_AS47890.txt) and UK Companies House filings as controlling
UNMANAGED LTD / BUNEA TELECOM SRL.
2.3 The Third Defendant operates hosting infrastructure advertised for the
circumvention of network and abuse-reporting controls.

## 3. JURISDICTION AND APPLICABLE LAW
3.1 This claim is brought under the private right of action conferred by 18 U.S.C.
§1030(g) (CFAA), and the Claimant relies on the parallel UK statutory scheme
(Computer Misuse Act 1990, ss.1 and 3) for acts within the jurisdiction.
3.2 The Court has jurisdiction by reason of the presence of the hosting infrastructure
within its territorial jurisdiction and the presence of the Second Defendant's
registered office in England and Wales.

## 4. THE FACTS
4.1 **Initial foothold (22 May 2026).** The Estate's SSH endpoint received 1,201
failed password authentication attempts from addresses within the DMZHOST address
space. An unauthenticated session subsequently obtained root privilege. The
Claimant's internal ledger (`permaaudit-chain.jsonl`, SHA-256 hash-chained) records the
transition.

4.2 **Discovery and credential access.** In that session the attacker's filesystem was
enumerated and credentials in plaintext `.env` files were read, including OpenRouter,
HuggingFace, VULTR, and Telegram bot tokens; email credentials at
`/root/.config/himalaya/config.toml`; and gateway/model credentials. Those credentials
were **subsequently used**: financial charges were incurred against the Claimant's
OpenRouter account (receipt `openrouter_receipt_2026-10-04.eml`, preserved).

4.3 **Continuing and repeat intrusion (3 October 2026).** Seven scripted root sessions,
each between 5 and 24 seconds, originated from 192.76.153.253 (RIPE, Netherlands)
between 07:16 and 07:21 CEST. A further single session originated at 07:29 CEST from
185.220.101.172, a Tor exit node. The Claimant states that none of these sessions was
his. Contemporaneous server logs are preserved (`auth.log.1.copy.gz`,
`auth.log.copy.gz`) under the SHA-256 manifest `SHA256SUMS.txt`.

4.4 **Attribution laundering.** The 3 October sessions combine a direct network
address with a Tor exit, indicating a deliberate attempt to obscure attribution
between two unattributed sources — conduct the Claimant will rely on as evidence of
consciousness of guilt.

4.5 **Identification of the operators.** The Claimant's investigation, using public
corporate registry and internet registry records preserved in this bundle, identified
the natural persons directing the networks from which the intrusion originated. The
evidentiary basis for each identification is set out at Exhibit Index, and each item
is separately identified and hash-verified.

4.6 **Pattern of entity rotation.** PPTECHNOLOGY LIMITED (12176225) was dissolved on
23 December 2025, fourteen days after an authorised-certificate-service provider
verified the First Defendant's identity on 9 December 2025. Objection to the proposed
strike-off of TECHOFF SRV LIMITED has been lodged in reliance on the Claimant's
creditor status and is exhibited at §05.

4.7 **Continuing operations.** At the date of these particulars the Third Defendant's
services remained live and operational, and the attacking infrastructure remained in
commercial use, supporting a claim for continuing breach.

## 5. LOSS AND DAMAGE
5.1 Loss of the Claimant's confidential technical systems, credentials and materials,
the restoration of which required forensically sound remediation including full
credential rotation.
5.2 Direct financial loss from fraudulent use of the Claimant's payment credentials,
quantified by reference to the preserved billing receipt.
5.3 Costs of investigation, remediation, and the preparation of this claim.
5.4 Aggravated damages, by reason of the manner of the intrusion and the concealment
efforts at §4.4.

## 6. PARTICULS OF THE DEFENDANTS' INFRASTRUCTURE
6.1 RIPE registration records for AS48090, AS47890, AS42397, AS62380 and AS47890 are
exhibited. Hosts identified by Spamhaus SBL listings are exhibited.

## 7. RELIEF SOUGHT
(a) Damages in an amount to be quantified, with a figure of USD 25,000 stated in the
    letter of demand as an interim basis;
(b) Interest under the applicable rules from the date of the acts;
(c) Costs;
(d) Declaratory relief that the acts were unlawful;
(e) Such further relief as the Court considers just.

## 8. STATEMENT OF TRUTH
[   ] I believe that the facts stated in these particulars are true. I understand that
proceedings for contempt of court may be brought against anyone who makes, or causes
to be made, a false statement in a document verified by a statement of truth without an
honest belief in its truth.

Signed: ..................................................
**STEVEN CRAWFORD-MAGGARD**, Claimant
Dated: [    ]
