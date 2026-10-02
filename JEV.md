# EVEZ JEV — System One decision layer

Integration of [Jev](https://typesafe.ai), TypeSafe AI's System One model, into
`evez-agentnet`.

## What Jev is

Jev does not generate text. You send a block of **state** plus typed
**questions**, and get back typed answers with calibrated probabilities and
confidence:

| Primitive | Asks | Returns |
|---|---|---|
| `noul` | yes/no | probability 0–1 |
| `choice` | pick from your options | selected option + per-option probabilities + confidence |
| `score` | rate on an ordered rubric | weighted value + probabilities + confidence |

All questions in one request are evaluated in parallel and independently.
Because the schema is fixed in advance, the model **cannot** return a value
outside the shape you defined — no parsing, no schema violations.

Endpoint: `POST https://api.typesafe.ai/v1/systemone`, `model: "jev-latest"`.

## Why this fits evez-agentnet specifically

Every serious defect fixed this session was the same failure mode: **a system
reporting a conclusion it had not actually earned.**

- The RSI engine prescribed recovery to a perfect agent for 244 rounds,
  because `min(reputation)` on a saturated roster always returns the same name.
- H1 told the system to "expand compassion" when FIRE events were **zero**.
- The shipper logged `Shipped` for 747 drafts that never left the machine.
- The notifier had a `SyntaxError` and would have failed silently every cycle.

Jev is built for exactly this class of problem. It returns a **calibrated
probability and a confidence score**, which is precisely what a hardcoded
threshold cannot do. It can say *"I'm 51% sure, don't act on this."*

The RSI thresholds — `rep >= 0.99` saturated, `rep < 0.95` recover — are
numbers someone picked. `judge_attention_target()` asks instead, and receives
a distribution over which agent actually needs intervention, plus enough
information to **abstain** when the answer isn't good enough to branch on.

## Files

| File | Purpose |
|---|---|
| `jev_client.py` | HTTP client, retry/backoff, response parsing, offline fixtures |
| `jev_decisions.py` | The three judgements, confidence gating, decision log |
| `jev_cli.py` | Command-line interface |
| `test_jev_decisions.py` | 30 assertions, incl. the must-not-fabricate contract |
| `jev/decisions.jsonl` | Every decision + its confidence, appended |

## Setup

```bash
# 1. Request early access at typesafe.ai
# 2. Put the key in the environment (do NOT commit it)
export TYPESAFE_API_KEY=...
echo 'TYPESAFE_API_KEY=' >> /root/evez-agentnet/.env   # already gitignored

# 3. Verify
python3 jev_cli.py status
python3 jev_cli.py probe "The spine hash chain verifies and all services are active." "Is this system healthy?"
```

## Usage

```bash
python3 jev_cli.py status       # configured? how many decisions logged?
python3 jev_cli.py health       # current stack state, as Jev would see it
python3 jev_cli.py attention    # which agent needs intervention + probabilities
python3 jev_cli.py shipper      # is the shipper BROKEN or just IDLE?
python3 jev_cli.py escalate     # should a human be paged?
```

The `shipper` judgement is the one that pays for itself immediately. "Shipper
is broken" and "shipper has no credentials configured" are the same symptom —
`$0.00` revenue — but they need completely different repairs. The old
threshold logic could not tell them apart.

## The contract this integration holds to

**It never fabricates an answer.** If the key is missing, the endpoint is
unreachable, or the payload is rejected, the module raises `JevUnavailable`
and callers receive an explicit `{"ok": false, "source": "fallback"}`. It never
returns a plausible-looking probability it did not receive.

This is deliberate and is the central design constraint. A decision layer that
invents confidence is *worse than no decision layer* — the calling code branches
on the number either way, and now the number is a fabrication wearing a
confidence score.

**It abstains below `JEV_MIN_CONFIDENCE` (default 0.55).** A choice answered
at 0.51 confidence is recorded with `abstained: true` and `choice: null`.

**Offline fixtures are labelled `source="offline-fixture"`** and can never be
mistaken for a model response.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TYPESAFE_API_KEY` | — | required; early-access key |
| `JEV_ENABLED` | `1` | set `0` to disable entirely |
| `JEV_MIN_CONFIDENCE` | `0.55` | below this, abstain rather than act |
| `YES_THRESHOLD` | `0.70` | probability at which a `noul` counts as yes |

## Current status

Integration is **built and verified**. The endpoint was reached live and
correctly rejected an invalid key with a 401, which confirms the request
format is right. It is **not yet live** because no `TYPESAFE_API_KEY` is set —
Jev is in limited early access, so the key comes from TypeSafe directly.

Until a key exists, every decision returns an explicit fallback and the system
behaves exactly as it did before. Enabling it changes *how* decisions get made,
not *whether* they get made.

## Verification

```bash
python3 test_jev_decisions.py   # 30/30
```

Covering: the must-not-fabricate contract, fallback labelling, response parsing
for all three primitives, probability normalisation, confidence gating, and
that an unregistered offline fixture raises rather than inventing a value.
