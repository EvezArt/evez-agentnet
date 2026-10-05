# Promotion Targets

This is the queue for turning unknowns into decidable states.

## P0: NAIAC delivery

Target artifact: original RFC-822/EML from the sending mailbox for the 2026-09-20 NAIAC nomination.

Minimum fields: Message-ID, To, Date, Received chain, SMTP/DSN result, attachment names/hashes.

Promotion path:

`UNKNOWN -> TRANSMISSION_PROVEN -> DELIVERY_PROVEN -> AGENCY_RECEIPT_PROVEN -> REVIEW_STATUS_KNOWN`

A successful local "Sent" record alone may establish transmission-to-provider, but not necessarily agency receipt.

## P0: US Tech Force delivery

Target artifact: original RFC-822/EML from the sending mailbox for the 2026-09-20 Tech Force communication.

Same minimum fields and promotion path as NAIAC.

Important correction: evidence involving a mistyped recipient address can establish that a message was attempted or bounced, but it does not establish rejection by the intended agency. Use the exact recipient address shown in the original envelope when classifying the event.

## P1: FOIPA

Target artifact: FBI determination or production/withholding notice associated with FOIPA 1758537-000.

Promotion path:

`ACKNOWLEDGED -> DETERMINATION_RECEIVED -> PRODUCTION_RECEIVED`

## P1: Uinta County

Target artifacts: county fee estimate, fulfillment message, released records, or formal denial/withholding notice.

Promotion path:

`FORM_RETURNED -> FEE_KNOWN -> FULFILLMENT_RECEIVED`

## P1: RFJ

Target artifact: SecureDrop account receipt for v2, then any analyst response.

Promotion path:

`V1_RECEIPT_RECORDED -> V2_RECEIPT_PROVEN -> ANALYST_RESPONSE_KNOWN`

## P1: IC3

Target artifact: IC3 automated acknowledgment or later FBI communication tied to the filing.

Promotion path:

`FILED -> ACKNOWLEDGED -> FBI_RESPONSE_KNOWN`

## P1: OpenRouter

Target artifacts: the provider ticket thread plus Activity/billing evidence identifying the charge source.

Promotion path:

`OPEN -> PROVIDER_IDENTIFIED_USAGE -> REFUND_GRANTED|DENIED`

No amount is to be upgraded from "documented" to "received" without a transaction artifact.

## Preservation rule

Every new source becomes a new event. Existing evidence is not edited to imply that the new event existed earlier.
