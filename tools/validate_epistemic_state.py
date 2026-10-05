#!/usr/bin/env python3
"""Validate the EVEZ 2026-10-05 epistemic-state control packet.

This is a lint gate, not a truth oracle. It checks schema integrity and
prevents accidental promotion of high-risk case states without explicit
primary-artifact references.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "evidence/2026-10-05/epistemic_state/state.json"

ALLOWED = {
    "UNKNOWN",
    "ACKNOWLEDGED",
    "FULFILLMENT_PENDING",
    "RECEIPT_RECORDED",
    "FILED_CONFIRMATION_PENDING",
    "OPEN_AWAITING_REPLY",
    "TRANSMISSION_PROVEN",
    "DELIVERY_PROVEN",
    "AGENCY_RECEIPT_PROVEN",
    "REVIEW_STATUS_KNOWN",
    "DETERMINATION_RECEIVED",
    "PRODUCTION_RECEIVED",
    "FEE_KNOWN",
    "ANALYST_RESPONSE_KNOWN",
    "FBI_RESPONSE_KNOWN",
    "PROVIDER_IDENTIFIED_USAGE",
    "REFUND_GRANTED",
    "REFUND_DENIED",
}

def fail(msg: str) -> None:
    raise SystemExit(f"epistemic-state validation failed: {msg}")

if not STATE.exists():
    fail(f"missing {STATE}")

data = json.loads(STATE.read_text(encoding="utf-8"))
if data.get("as_of") != "2026-10-05":
    fail("unexpected as_of")
doctrine = data.get("doctrine")
if not isinstance(doctrine, dict):
    fail("missing doctrine object")
for key in (
    "claimed_ne_measured_ne_replicated_ne_explained",
    "provenance_ne_truth",
    "submission_ne_delivery_ne_receipt_ne_review_ne_selection_ne_appointment",
):
    if doctrine.get(key) is not True:
        fail(f"doctrine flag {key} must be true")

cases = data.get("cases")
if not isinstance(cases, list) or not cases:
    fail("cases must be a non-empty list")

ids = set()
for case in cases:
    if not isinstance(case, dict):
        fail("case is not an object")
    cid = case.get("id")
    if not cid or cid in ids:
        fail(f"duplicate or missing case id: {cid!r}")
    ids.add(cid)
    state = case.get("state")
    if state not in ALLOWED:
        fail(f"{cid}: unsupported state {state!r}")
    if not case.get("entity"):
        fail(f"{cid}: missing entity")
    if not isinstance(case.get("known"), list):
        fail(f"{cid}: known must be a list")
    if not isinstance(case.get("missing"), list):
        fail(f"{cid}: missing must be a list")
    if not case.get("source"):
        fail(f"{cid}: missing source")

# High-risk external-status gate.
for cid in ("naiac-2026-09-20", "tech-force-2026-09-20"):
    case = next((c for c in cases if c.get("id") == cid), None)
    if case is None:
        fail(f"required case missing: {cid}")
    if case["state"] != "UNKNOWN":
        fail(f"{cid}: must remain UNKNOWN until a primary delivery/receipt artifact is attached")
    missing = " ".join(str(x).lower() for x in case["missing"])
    for phrase in ("original mailbox", "delivery", "receipt"):
        if phrase not in missing:
            fail(f"{cid}: missing-artifact list no longer names {phrase!r}")

print(f"OK: validated {len(cases)} case states; high-risk nomination states remain UNKNOWN.")
