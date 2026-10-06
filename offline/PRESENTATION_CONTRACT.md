# EVEZ Pocket: Witness-Preserving Presentation Contract

This document defines the boundary between an artifact and its device presentation.

## Invariant

    CANONICAL_BYTES != PRESENTATION_BYTES

The canonical artifact is the authoritative local record. Presentation may add
watermarks, layout, typography, device labels, or other display metadata without
changing the canonical artifact.

## Transform

    A
    |
    | SHA-256(EVEZ/OFFLINE/PRESENTATION/v1 + canonical(A))
    v
    H(A)
    |
    +--> watermark(H(A), device, presentation_id)
    |
    v
    P(A)

The watermark identifies A. It does not become part of A.

## Required states

    CAPTURED       canonical content exists
    HASHED         canonical digest computed
    PRESENTED      device-native representation produced
    WATERMARKED    provenance visibly attached
    EXPORTED       optional copy leaves the device

A presentation failure must never rewrite or silently replace CAPTURED data.

## Device boundary

The device is part of presentation context, not evidence content, unless the
user explicitly records device information as evidence.

The default device label is EVEZ-POCKET and may be overridden with
EVEZ_DEVICE_LABEL. No precise location is required.

## Verification

Given canonical content A and the recorded artifact_hash:

    artifact_hash == SHA-256(domain || canonical(A))

must remain true after any number of presentation transformations.

A renderer can therefore change screen dimensions, font, wrapping, watermark
placement, or export format while preserving the identity of the underlying
artifact.

## Why this matters

This makes the watermark an epistemic witness rather than an edit.

The system can answer two different questions without conflating them:

    "What was recorded?"       -> canonical artifact
    "How was it presented?"    -> presentation + watermark metadata

That separation is the product boundary for EVEZ Pocket.
