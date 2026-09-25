from tools.lord_identity import situated_character,identity_record,lord_directive,succession_rule

def test_characters_remain_distinct():
    r=situated_character(identity="Steven/EVEZ",system_role="LORD",continuity_refs=["repo:1"])
    assert r["identity"]=="Steven/EVEZ"
    assert r["system_role"]=="LORD"
    assert r["relation"]=="SITUATED_IN"
    assert r["identity"] != r["system_role"]

def test_identity_is_hypothesis():
    r=identity_record(identity="Steven/EVEZ",continuity_refs=["repo:1"])
    assert r["identity_status"]=="HYPOTHESIS"
    assert r["system_role"]=="LORD"

def test_directive_is_scoped():
    r=lord_directive(principal="Steven/EVEZ",objective="preserve evidence",action="append_event",
      authorization_ref="auth:1",evidence_refs=["obs:1"])
    assert r["governing_role"]=="LORD"
    assert r["principal"]=="Steven/EVEZ"
    assert r["authority"]=="SCOPED_NOT_GLOBAL"
    assert r["status"]=="AUTHORIZED_PENDING_EFFECT"

def test_successor_is_not_auto_promoted():
    r=succession_rule(old_model="m0",new_candidate="m1",tests=["t1"],evidence_refs=["e1"])
    assert r["promotion"].startswith("DEFERRED")

if __name__=="__main__":
    test_characters_remain_distinct();test_identity_is_hypothesis()
    test_directive_is_scoped();test_successor_is_not_auto_promoted()
    print("ok: lord identity kernel")
