# EVEZ Pocket Agent

A tiny, local-first personal agent designed for the exact hardware constraint most AI products pretend does not exist: an ordinary Android phone with limited RAM, storage, battery, and money.

## Product proposition

EVEZ Pocket is not "another chatbot."

It is:

**private local chat + persistent memory + auditable action history + zero per-token cloud bill.**

The base runtime is free and open. The commercial wedge is the managed setup, hardened evidence workflow, and optional hosted synchronization for users who need it.

## Why this can sell

The product attacks four recurring costs at once:

1. API spend: local inference removes per-message cloud charges.
2. Data exposure: conversations can remain on-device.
3. Infrastructure: the core UI/runtime needs no database or cloud backend.
4. Lock-in: the model server is an interchangeable local HTTP boundary.

The differentiator is the evidence layer. Ordinary local chat forgets what happened. EVEZ records the interaction path and can distinguish UNKNOWN from observed evidence.

## First paid offer

**EVEZ Pocket Setup — $19 one-time**

Deliverable:
- install script
- compact local model setup
- device-specific configuration
- evidence ledger enabled
- export/backup procedure
- one troubleshooting pass

This is intentionally small enough to buy without a procurement committee, because procurement committees are where simple products go to die.

## Recurring offer

**EVEZ Pocket Pro — $6/month**

Adds:
- signed/exportable evidence bundles
- encrypted remote backup when explicitly enabled
- cross-device synchronization
- update channel
- hosted diagnostics
- priority support

The offline base must remain useful without the subscription. Paid features should add convenience and durable infrastructure, not cripple the local product.

## Revenue math

At $19 setup:
- 10 customers = $190
- 50 customers = $950
- 100 customers = $1,900

At $6/month:
- 50 subscribers = $300 MRR
- 100 = $600 MRR
- 500 = $3,000 MRR
- 1,000 = $6,000 MRR

These are arithmetic scenarios, not forecasts.

## Immediate distribution wedge

Do not start by selling "AI."

Sell a concrete outcome:

> Run your own private ChatGPT-style assistant on the Android phone you already own, without paying an API bill for every message.

The first audience is people who:
- already use Termux or local AI,
- care about privacy,
- have old Android hardware,
- are frustrated by API bills,
- need persistent notes/actions rather than another disposable chat window.

## Technical moat

The moat is not the tiny model. Models are commodities.

The moat is the provenance path:

    message
      -> observable intent
      -> selected action
      -> execution path
      -> result
      -> correction
      -> immutable witness
      -> trajectory evidence

That architecture survives model replacement.

## Hard truth

A local 0.5B model will not outperform frontier models at general reasoning. The product therefore should not compete on raw intelligence.

It competes on:
- cost,
- privacy,
- ownership,
- persistence,
- auditability,
- hardware accessibility.

That is a much more defensible product boundary.
