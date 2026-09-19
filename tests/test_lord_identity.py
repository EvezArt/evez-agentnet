from tools.lord_identity import identity_record,lord_directive,succession_rule

def test_identity_is_hypothesis():
    r=identity_record(identity="Steven/EVEZ",continuity_refs=["repo:1"])
    assert r["identity_status"]=="HYPOTHESIS"

def test_directive_is_scoped():
    r=lord_directive(principal="Steven/EVEZ",objective="preserve evidence",action="append_event",
      authorization_ref="auth:1",evidence_refs=["obs:1"])
    assert r["authority"]=="SCOPED_NOT_GLOBAL"
    assert r["status"]=="AUTHORIZED_PENDING_EFFECT"

def test_successor_is_not_auto_promoted():
    r=succession_rule(old_model="m0",new_candidate="m1",tests=["t1"],evidence_refs=["e1"])
    assert r["promotion"].startswith("DEFERRED")

if __name__=="__main__":
    test_identity_is_hypothesis();test_directive_is_scoped();test_successor_is_not_auto_promoted()
    print("ok: lord identity kernel")
