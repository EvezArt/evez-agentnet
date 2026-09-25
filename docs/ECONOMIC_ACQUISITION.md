# EVEZ Economic Acquisition Engine

This is the executable economic layer for the EVEZ evidence architecture.

## Core state machine

```
OPPORTUNITY_DISCOVERED
        |
        v
OPPORTUNITY_VERIFIED
        |
        v
BUYER_QUALIFIED
        |
        v
OFFER_PROPOSED
        |
        v
OFFER_ACCEPTED
        |
        v
DELIVERY_COMMITTED
        |
        v
DELIVERABLE_VERIFIED
        |
        v
INVOICE_ISSUED
        |
        v
PAYMENT_OBSERVED
        |
        v
RELATIONSHIP_RENEWED
```

A branch may instead become BLOCKED, REJECTED, STALE, or CONTRADICTED.

## Economic truth boundary

The system does not collapse these states:

```
observed opportunity
      != proposed price
      != accepted contract
      != issued invoice
      != observed payment
```

Only PAYMENT_OBSERVED with `amount_semantics=RECEIVED` contributes to observed cash.

## Provenance chain

```
PAYMENT
  <- INVOICE
  <- CONTRACT
  <- ACCEPTED OFFER
  <- DELIVERED ARTIFACT
  <- VERIFIED CAPABILITY
  <- QUALIFIED OPPORTUNITY
  <- OBSERVED SOURCE
```

Every hop must remain addressable through source, evidence, provenance, and parent-event references.

## Acquisition boundary

The engine may read authorized public observations and normalize opportunities. It may generate an offer draft and identify the next verification step.

It does not autonomously:
- send outreach
- sign contracts
- issue invoices
- move money
- bypass authentication or access controls
- fabricate buyer identity, budget, revenue, or delivery status

Consequential external actions require explicit human approval.

## Commands

```
python tools/economic_spine.py --ledger docs/economy/economic-events.jsonl verify
python tools/economic_spine.py --ledger docs/economy/economic-events.jsonl money
python tools/opportunity_engine.py --input observation.jsonl --capability "evidence audit" --capability "automation"
python tools/economic_reducer.py --ledger docs/economy/economic-events.jsonl
python tools/economic_spine_test.py
```

The acquisition queue is a machine-readable event surface, not a pretend CRM. The useful unit is a verified state transition with evidence attached.
