# Integration Notes — Vercel and Stripe

## Vercel Runtime Notes
Relevant implementation patterns for the EVEZ runtime:
- secure cron endpoints should verify an Authorization header against `CRON_SECRET`
- production cron execution only runs on production deployments
- Next.js route handlers are the natural fit for bounded runtime endpoints
- remote caching can be applied selectively to API routes where derived data is safe to cache

Recommended first runtime tie-in:
1. deploy route handlers to production
2. add a secured cron route for scheduled `cycle-v4`
3. keep cycle operations idempotent
4. record success/failure in receipts

## Stripe Low-Risk Monetization Path
Recommended initial scope:
- create products
- create prices
- create payment links
- create invoices and invoice items only after explicit operator review

Guidance:
- treat products and prices as the durable catalog layer
- create new prices instead of mutating the amount on old prices
- archive obsolete prices rather than attempting to delete used ones
- use webhooks to verify payment state instead of trusting client-side return paths

## High-Risk Actions That Stay Gated
Do not enable without explicit approval and audit rails:
- autonomous refunds
- autonomous subscription cancellation or modification
- speculative trading or exchange execution
- off-session or irreversible financial actions without human review

## Agentic Fit
The payment layer should remain downstream of:
1. internal verification
2. policy checks
3. human approval gate when risk or irreversibility is present
