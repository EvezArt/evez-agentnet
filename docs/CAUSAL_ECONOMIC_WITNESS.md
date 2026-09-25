# EVEZ Causal Economic Witness

This layer couples economic state to the EVEZ evidence model without collapsing opportunity, contract, invoice, and received money.

Lifecycle:
REALITY_WITNESS -> OPPORTUNITY_PROPOSED -> CAPABILITY_MATCH -> HUMAN_APPROVAL -> CONTRACT -> DELIVERY -> OBSERVATION -> VERIFICATION -> INVOICE -> OBSERVED_PAYMENT -> REPUTATION_UPDATE -> CAPABILITY_MUTATION

Money state is a separate axis:
PROPOSED -> CONTRACTED -> INVOICED -> RECEIVED

Hard boundaries:
- A proposal is not an observation.
- A contract is not an invoice.
- An invoice is not a payment.
- Projected money is not cash.
- Payment does not independently prove delivery quality.
- Delivery does not imply payment occurred.
- Simulation cannot become reality through narration.
- Capability configuration does not prove capability effectiveness.
- Unknown does not become false because nobody looked.

Append-only semantics are represented as transition events. A transition records previous_state, next_state, reason, timestamp, and evidence references. Existing events are not edited. A current state is a derived view over history.

External commitment is human-gated. The module records an approval decision and scope but does not sign contracts, send outreach, invoice customers, or move money.

Causal receipts point backward to upstream opportunity/capability/contract evidence and forward to delivery/payment evidence. The receipt only claims a delivery-to-payment path when delivery is independently verified and payment is independently observed.

A capability mutation remains PROPOSED until verification evidence is supplied. This keeps successful work from silently rewriting the capability ontology.
