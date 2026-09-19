#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.self_audit import audit

def test_self_audit_has_enforced_boundaries():
    findings={x["code"]:x["status"] for x in audit(Path(__file__).resolve().parents[1])}
    assert findings["CHAIN_CONTENT_ORDER"]=="ENFORCED"
    assert findings["TIMESTAMP_ASSERTION"]=="ENFORCED"
    assert findings["CHAIN_SHAPE"]=="ENFORCED"
    assert findings["NULL_OBSERVATION"]=="ENFORCED"
    assert findings["VERIFICATION_ORDER"]=="ENFORCED"
    assert findings["SELF_AUDIT_CI"]=="ENFORCED"
    assert findings["POLICY_ENFORCEMENT"]=="ONTOLOGY_BREAK_CANDIDATE"

if __name__=="__main__": test_self_audit_has_enforced_boundaries(); print("ok: self-audit")
