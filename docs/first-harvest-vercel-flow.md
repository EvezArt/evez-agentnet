# First Harvest Vercel Flow

This is the concrete scaffold for the first versioned skill:

- `stablecoin_dislocation_v1`

## Why this assertion first

It is the cleanest measurable primitive in the current stack:

- observable without privileged execution infrastructure
- easy to state as a binary assertion
- robust under inversion and skepticism
- useful in profit, safety, and neutral modes

Assertion:

```text
normalized net-executable USDC/USDT spread > 2.5% for >=30s across >=2 venues
```

`net-executable` means after estimated fees and slippage.

## Files

- `api/first-harvest.ts` — Vercel handler scaffold
- `flows/first-harvest.flow.json` — flow graph
- `schemas/first-harvest-trigger.schema.json`
- `schemas/first-harvest-proof.schema.json`
- `schemas/first-harvest-receipt.schema.json`
- `demo/first_harvest_event.json` — sample webhook payload

## Run shape

```text
Webhook
→ Normalize Quotes
→ Binary Assertion
→ Self-Consistency Check
→ if fail: TEST / alert / retry
→ Invariance Battery
→ if fail: HOLD TEST + defeater trace
→ if pass: MINT_CANDIDATE
→ Ledger Commit
→ Emit Proof + Receipt
```

## Example local invocation

If deployed on Vercel:

```bash
curl -X POST https://your-deployment.vercel.app/api/first-harvest \
  -H 'content-type: application/json' \
  --data @demo/first_harvest_event.json
```

## What the handler returns

- normalized quote surface
- assertion result
- self-consistency result
- invariance battery result
- mint candidate status if passed
- ledger commit hashes
- proof artifact payload
- receipt artifact payload

## What becomes possible only through the whole system

A flat detector can say a spread exists.
The governed runtime can do more:

1. refuse action under principled uncertainty
2. mint a versioned skill instead of a raw signal
3. preserve rival futures instead of flattening them
4. feed RSI speculation back into runtime state
5. generate build pressure from within the daemon
6. emit proof / receipt / dashboard / digest surfaces

That is the real difference between a detector and a governed cognitive runtime.
