# Governed runtime demonstration

This folder demonstrates what the cognition-governed `evez-agentnet` stack can actually do.

It is not a theory folder. It shows:

1. a concrete signal packet
2. a cognition-aware prediction packet with rival futures
3. RSI hypotheses that get pushed back into branch state
4. example generated deliverables
5. a sample proof / receipt / governance trail

## Demo flow

```text
sample_scan_results.json
→ sample_prediction_packet.json
→ sample_rsi_hypotheses.json
→ generated_outputs/
→ sample_runtime_receipt.json
```

## What to inspect

- `sample_scan_results.json` — what the runtime can ingest
- `sample_prediction_packet.json` — how it preserves ranked opportunities and uncertainty
- `sample_rsi_hypotheses.json` — how speculation becomes branch material
- `generated_outputs/` — writing and artifact examples
- `sample_runtime_receipt.json` — what governance and lineage look like after a governed round

## Why this matters

Most agent repos show architecture but not the actual outputs that prove the system can write, draft, gate, and explain itself.
This folder exists to make those capabilities inspectable.
