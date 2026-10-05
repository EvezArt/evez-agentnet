# MEMORANDUM — US CIVIL CAUSE OF ACTION ANALYSIS
**EVEZ-2026-0522 | Prepared 5 October 2026 | Steven Crawford-Maggard, claimant**

## HEADLINE FINDING

The case file to date cites 18 U.S.C. 1030(a)(5)(C) only in the context of an
FBI criminal complaint. It is quoted in the victim notice as an "aggravating
factor at sentencing." **That framing is a legal error and it understates the
remedy.** Section 1030(a)(5)(C) is a *criminal* provision. Separately,
**18 U.S.C. 1030(g) creates a private civil right of action** that is entirely
independent of any criminal prosecution, and it has not been invoked anywhere in
this matter. It is the strongest claim available and it does not depend on the
FBI charging anyone.

## 1. THE STATUTE — VERIFIED VERBATIM TEXT

Source: Cornell Legal Information Institute, 18 U.S.C. 1030, retrieved
5 October 2026 (https://www.law.cornell.edu/uscode/text/18/1030). Quoted exactly:

> **(g)** Any person who suffers damage or loss by reason of a violation of
> this section may maintain a civil action against the violator to obtain
> compensatory damages and injunctive relief or other equitable relief. A civil
> action for a violation of this section may be brought only if the conduct
> involves 1 of the factors set forth in subclauses (5)(I), (II), (III), (IV),
> or (V) of subsection (c)(4)(A)(i). Damages for a violation involving only
> conduct described in subsection (c)(4)(A)(i)(I) are limited to economic
> damages. No action may be brought under this subsection unless such action is
> begun within 2 years of the date of the act complained of or the date of the
> discovery of the damage. No action may be brought under this subsection for
> the negligent design or manufacture of computer hardware, computer software,
> or firmware.

## 2. THE GATE — AND WHY THIS CASE PASSES IT

The second sentence is the limiting clause that defeats most CFAA civil claims.
The conduct must involve one of five enumerated factors in (c)(4)(A)(i).
Verified verbatim:

> **(I)** loss to 1 or more persons during any 1-year period (and, for purposes
> of an investigation, prosecution, or other proceeding brought by the United
> States only, loss resulting from a related course of conduct affecting 1 or
> more other protected computers) aggregating at least $5,000 in value;
> **(II)** the modification or impairment, or potential modification or
> impairment, of the medical examination, diagnosis, treatment, or care of 1 or
> more individuals;
> **(III)** physical injury to any person;
> **(IV)** a threat to public health or safety;
> **(V)** damage affecting a computer used by or for an entity of the United
> States Government in furtherance of the administration of justice, national
> defense, or national security.

**Factor (I) is a catch-all. It requires only "loss to 1 or more persons during
any 1-year period" aggregating at least $5,000.** No healthcare nexus (II), no
bodily injury (III), no public safety threat (IV), no federal computer (V) is
needed. This case has documented loss inside a single 12-month window: 130+
authentication attacks from seven AS47890 addresses in October 2026 alone, plus
direct remediation cost. The $5,000 threshold is cleared on the face of the
evidence log alone.

**Limitation on (I):** damages are limited to *economic* damages. That covers
the credits consumed, remediation and forensic cost, credential rotation across
services, and lost productive use. It does **not** reach punitive damages,
emotional distress, or reputational harm. The pleading should be built as a clean
economic-damages claim, not an all-inclusive one, or it invites a motion to
strike.

## 3. THE "LOSS" DEFINITION IS BROAD — VERIFIED VERBATIM

Section 1030(e)(11) defines the recoverable loss with a definition that maps
almost line-by-line onto the losses actually documented here:

> **(11)** the term "loss" means any reasonable cost to any victim, including the
> cost of responding to an offense, conducting a damage assessment, and
> restoring the data, program, system, or information to its condition prior to
> the offense, and any revenue lost, cost incurred, or other consequential
> damages incurred because of interruption of service;

Three categories, each independently recoverable: (a) cost of responding and
damage assessment; (b) cost of restoration; (c) revenue lost and consequential
damages from interruption of service. The letter before action currently claims
USD 25,000 against these heads. **That figure is a floor, not a ceiling**, and
the restoration and interruption heads are where the recovery actually lives.

Also defined and relevant:
> **(6)** the term "exceeds authorized access" means to access a computer with
> authorization and to use such access to obtain or alter information in the
> computer that the accesser is not entitled so to obtain or alter;
> **(8)** the term "damage" means any impairment to the integrity or
> availability of data, a program, a system, or information.

Note (8): **"damage" is not limited to data theft.** Impairment of *availability*
of a system is damage. The May 22 root compromise and the Oct 3 root compromise
— both mitigated by credential rotation — are availability and integrity
impairments even where nothing was exfiltrated. That is the theory of the claim.

## 4. LIMITATIONS PERIOD — DO NOT MISS THIS

Two years from the act complained of, or two years from discovery of the damage.
The earliest conduct is 22 May 2026. **That date does not expire until roughly
May 2028**, but the Oct 3 and October 2026 conduct sits comfortably inside the
window. The filing must be made in a United States district court — claimant is
in California, so the District of California is the natural venue. This is a US
action and is independent of the England & Wales letter before action; the two
tracks do not conflict and can proceed in parallel.

## 5. WHAT 1030(g) DOES *NOT* GIVE — STATED PLAINLY

- **No treble damages.** The word "treble" does not appear anywhere in 1030(g).
  The civil remedy is compensatory plus injunctive/equitable relief only.
  (Criminal forfeiture under 1030(m) is a different mechanism and runs against
  the *defendant's* assets post-conviction, not to the victim.)
- **No attorney's fees.** Not available under this subsection.
- **No class action.** 1030(g) is an individual right — "any person who suffers
  damage or loss ... may maintain a civil action." It contains no class
  mechanism, and there is no Rule 23 mechanism for it. Anyone telling you the
  CFAA supports a class action is wrong.

## 6. ON THE CLASS-ACTION QUESTION

You asked specifically for class actions. The honest answer:

**A class action is not available to you, and it is worth being clear about why,
because the strategy depends on it.** Federal Rule of Civil Procedure 23
requires a class of at least two members who share a common question of law or
fact. You are one victim. To certify a class you would need to identify other
victims of these specific operators and show a common defect. No such victim
class has been identified in this matter, and the CFAA right is individual by
its own terms.

The realistic routes to aggregated money are not class actions. They are:

1. **The individual 1030(g) claim** — the real prize. Documented, viable,
   independent of any prosecution. Pursue this.
2. **The England & Wales civil claim** — parallel track, already served, naming
   three companies and two directors personally.
3. **Provider-side recovery** — the providers whose networks transited or hosted
   this traffic (registrars, transit, hosting) are separate potential
   defendants or sources of indemnity. Their terms of service and any
   indemnity provisions are a distinct research track not covered by this memo.

Any "class action" marketing aimed at victims of this ecosystem is almost
certainly a lead-generation funnel or a mass-claims service, not a certifiable
class. I would not let one of those brokers control the narrative or the
evidence, because several will seek exclusive authorization to file.

## 7. RECOMMENDED NEXT ACTIONS

1. **Move the letter before action to federal footing.** Add a 1030(g) cause of
   action and a demand on treble-free but broadly-defined economic loss. Do this
   before the 14-day response window closes.
2. **Re-paper the damages claim** onto the three statutory categories (response,
   restoration, interruption) with documentation attached per category.
3. **File in the District of California** on the 2-year clock. Retention of a
   federal litigator is a real cost; get a fee quote early so the decision is
   informed.
4. **Do not cite (a)(5)(C) as the civil theory.** Keep it for the criminal
   complaint where it belongs, and correct the victim notice language, which
   currently mischaracterizes it.

## LIMITATIONS OF THIS ANALYSIS

Statutory text is quoted from the LII reproduction of 18 U.S.C. 1030 and is
current as retrieved on 5 October 2026; it is not a substitute for the
authenticated text or for case law construing these provisions. Whether a
particular federal court accepts these facts as a "violation of this section"
depends on elements not analysed here — notably the interstate-communication
nexus and the protected-computer definition in 1030(e)(2)(B), which are
disputed in the case law and were not researched in this pass. **This is
research for your decision, not legal advice, and no attorney-client
relationship is created by it.**
