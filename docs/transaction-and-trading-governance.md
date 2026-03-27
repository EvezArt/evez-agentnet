# Transaction and Trading Governance

## Intent
The system may prepare transaction and trading proposals, but it must not silently spend, transfer funds, or execute trades without explicit approval.

## Allowed Without Additional Approval
Low-risk preparation work:
- product and price planning
- payment link proposals
- customer creation proposals
- invoice preparation proposals
- internal ledgering
- receipt generation
- non-executing trade proposals

## Requires Human Approval
- invoice finalization
- refunds
- subscription changes
- outbound payment or transfer execution
- order placement on any exchange or broker
- crypto transfers
- currency conversion or trade execution

## Required Evidence Before Approval
Every proposal should include:
- action kind
- operator summary
- payload details
- risk tier
- justification / thesis
- internal verification result
- receipt trail

## Runtime Pattern
1. propose action
2. write approval request
3. persist proposal to memory
4. emit receipt with `pending_approval`
5. wait for explicit approval or rejection
6. only then bind to external execution surface

## Reasoning Doctrine
The system can think, compare, model, and prepare at high speed.
Execution remains governed where the consequences are financial, legal, or irreversible.
