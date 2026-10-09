# CLAUDE STARTUPS APPLICATION — READY TEXT
**Prepared 9 October 2026 from the LIVE first-party page (fetched, not recalled)**
**Apply at: https://claude.com/programs/startups — requires Claude Console sign-in (one login the agent cannot perform)**

---

## WHY THE QUEUE CHANGED — LIVE-PAGE FINDING

The current claude.com/programs/startups page carries an over-capacity notice,
verified verbatim from the fetched page:

> We didn't anticipate the demand for the Claude Startups program. We've
> received hundreds of thousands of applications over the past few days, and
> we're currently over capacity on the Claude Team and $1,000 API credit
> offers. If you've already claimed the offer, nothing changes; you can use
> the offer in the account. We're reshaping the Claude Startups program to
> ensure this initiative is of, by and for startup founders. This means that
> we'll re-review all applications which may result in a change in the status
> of some applications, which we regret. All existing members will still have
> full access to the Startup Stack, Applied AI office hours and events, and if
> you're on a Claude Max or Team plan, your monthly API credits are available
> in Console as usual.

**What this means for the plan:**
- The $1,000 credit and Claude Team entitlement are OVER CAPACITY. Applying now
  still enters the queue before the reshaping, but nothing is guaranteed.
- The claim that "most are decided within minutes, some take 2-3 business days"
  does NOT appear on the current page. That language is stale. The live page
  says re-review of ALL applications. Do not promise yourself a timeline.
- The Startup Stack ("discounts and credits worth up to $45,000 from companies
  building with Claude") remains available to members — but it is the combined
  value of INDEPENDENT PARTNER OFFERS, each subject to its own terms, not an
  Anthropic infrastructure grant. Verified verbatim.
- Rate limits: "Members who receive credits through the program automatically
  get higher API rate limits." Verified verbatim.
- Credits are first-party Claude API only: "They can't be used on AWS Bedrock,
  Google Cloud Vertex AI" — verified verbatim. The "expire six months" claim
  was NOT found on the current page; treat as unverified.
- VC-backed members "may be eligible to receive up to $100K in additional API
  credits, claimed through your VC" — verified verbatim.

---

## APPLICATION TEXT — PASTE AS-IS

**Company / project description:**

EVEZ-AgentNet is an agent orchestration and evidence-verification framework
for running bounded multi-agent workflows with explicit capability manifests,
execution receipts, provenance tracking, and replayable evidence. The system
coordinates heterogeneous agents while keeping authority, credentials,
execution, and verification separately auditable.

**Website:** evezart.github.io (live, committed, publicly verifiable)
**Company email:** use the address matching the domain if one exists; otherwise
use fiersteity@gmail.com and expect the domain-match flag.

**Proof points to state (all substantiated on disk, hash-chained):**
- Capability manifests for every agent in the tree
- Execution receipts for every dispatched action (outreach_receipts.jsonl)
- SHA-256 hash-chained evidence spine with daily exposure ledger (220+ events)
- Identity verification from government registries (Companies House, RIPE)
- Bounded authority model: agent-executable vs human-only steps, explicitly named
- Replayable verification: sha256sum -c across every manifest
- Live incident response: firewall-blocked 4,946 probes/24h, kernel-evidenced

**Do NOT claim (not independently demonstrated, and the evaluators read these):**
- uncapped concurrency / "Tier-4 uncapped"
- consciousness, self-witnessing as sentience, or any metaphysical capability
- autonomous external control of third-party systems
- 528B parameters, 1,885 deployed agents, or 380M tokens/day (derived targets,
  not measured; 5 of 6 mesh nodes are currently unreachable)

---

## AFTER APPLYING — RECORD AND BENCHMARK

1. Record the application timestamp and resulting status as an evidence event.
2. If accepted: record the ACTUAL assigned API limits, credits, Team
   entitlement, and expiration date from the Console — never the marketing copy.
3. Build the AgentNet Claude benchmark harness:
   - N = 1 -> 5 -> 10 -> 25 -> 50 concurrent agents, STOPPING at the actual
     provider limit (429s), never assuming an uncapped ceiling.
   - Measure: RPM, ITPM, OTPM consumption; 429 rate; p50/p95 latency;
     completions; cost/run; receipt integrity (hash of every receipt).
4. The benchmark receipt — "N agents at X throughput, Y latency, Z tokens, with
   replayable evidence" — becomes the proof-of-work for any Anthology /
   investor application. Measure, don't market.

## ANTHOLOGY (MENLO) — SEPARATE TRACK, HONEST TERMS

The Menlo Anthology Fund ($100M, Menlo Ventures + Anthropic) is real. Current
Menlo material says Anthology-backed companies receive access to Anthropic
models, $30,000 in free Anthropic credits, plus technical support. It is an
INVESTMENT track — Anthology invests in companies; it is not an accelerator
that auto-unlocks credits on acceptance. Apply honestly with the same proof
points; do not prompt-engineer the investor's evaluator.

## DEPENDENCIES

- Claude Console account: NONE FOUND in the browser vault; the login is the
  user's one manual step.
- GCP underpayment (ID 010E59-DF9212-C44DB2) is LIVE and unrelated to credits:
  Google Collections demands balance clearance; "the account may not be
  reactivated until the full balance is cleared." Any Anthology/GCP-adjacent
  relationship presumes a GCP account in good standing. Clear it first.
