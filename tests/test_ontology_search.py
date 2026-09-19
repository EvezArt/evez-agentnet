#!/usr/bin/env python3
from tools.ontology_search import successor_candidate,representation_pressure,audit_of_audit,compare_candidates

def test_candidate_is_not_declared_true():
    c=successor_candidate(break_id="break:1",prior_model="model:old",observation={"kind":"boundary"},
      failed_representation="old-category",distinction="source-layer-split",
      discriminator="compare independent witnesses",falsification_condition="same result across all source layers",
      evidence_refs=["obs:1"])
    assert c["status"]=="PROPOSED" and c["successor_model"] is None
    assert c["authority"]=="CLAIM_LOCAL_ONLY"

def test_pressure_has_no_fake_score():
    p=representation_pressure(exception_count=2,contradiction_count=3,repeated_failure_count=1,unresolved_boundary_count=4)
    assert p["score"] is None and p["authority"]=="NONE"

def test_audit_of_audit_requires_traceability():
    r=audit_of_audit(audit_ref="audit:1",findings=[{"code":"X","status":"ENFORCED","evidence":["ev:1"]}],
      evidence_index={"ev:1":["repo:file:1"]},test_index={"X":["test:1"]})
    assert r["checks"][0]["evidence_traceable"] and r["checks"][0]["test_traceable"]
    assert r["successor_model"] is None

def test_candidates_are_not_ranked():
    r=compare_candidates([{"candidate_id":"a","discriminator":"d1","falsification_condition":"f1"},
      {"candidate_id":"b","discriminator":"d2","falsification_condition":"f2"}],[{"observation_ref":"obs:1"}])
    assert r["winner"] is None and r["selection"].startswith("DEFERRED")

if __name__=="__main__":
    test_candidate_is_not_declared_true(); test_pressure_has_no_fake_score()
    test_audit_of_audit_requires_traceability(); test_candidates_are_not_ranked()
    print("ok: ontology search")
