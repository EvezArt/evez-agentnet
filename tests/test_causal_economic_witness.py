#!/usr/bin/env python3
from tools.causal_economic_witness import CausalError, approval_gate, causal_receipt, capability_update, economic_state, payment_observation, transition

def expect_error(fn):
    try: fn()
    except CausalError: return
    raise AssertionError("expected CausalError")

def main():
    assert economic_state("opp-1","PROPOSED",amount=6000,currency="USD")["state"] == "PROPOSED"
    expect_error(lambda: economic_state("opp-1","RECEIVED",amount=6000,currency="USD"))
    assert transition("opp-1",previous_state="INVOICED",next_state="RECEIVED",
                      evidence_refs=["payment:tx-1"],reason="bank statement observed",
                      observed_at="2026-09-19T00:00:00Z")["next_state"] == "RECEIVED"
    expect_error(lambda: transition("opp-1",previous_state="RECEIVED",next_state="CONTRACTED",
                                    evidence_refs=["x"],reason="regression",
                                    observed_at="2026-09-19T00:00:01Z"))
    expect_error(lambda: causal_receipt(receipt_id="r1",opportunity_id="opp-1",
                                        upstream_refs=["contract:1"],downstream_refs=["payment:1"],
                                        verified_delivery=False,observed_payment=True))
    assert payment_observation("opp-1",amount=2500,currency="USD",
                               payment_evidence_refs=["bank:statement:1"],
                               observed_at="2026-09-19T00:00:00Z")["claim"] == "RECEIVED"
    assert approval_gate("opp-1",approver_ref="human:1",decision="APPROVED",
                         approved_scope={"max_amount":2500})["decision"] == "APPROVED"
    assert capability_update("cap-1",mutation="deliver automation",delivery_refs=["delivery:1"],
                             verification_refs=[],environment="production")["state"] == "PROPOSED"
    assert capability_update("cap-1",mutation="deliver automation",delivery_refs=["delivery:1"],
                             verification_refs=["verification:1"],environment="production")["state"] == "VERIFIED"

if __name__ == "__main__":
    main()
