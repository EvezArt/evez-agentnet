#!/usr/bin/env python3
"""Generate testable successor representations without selecting a winner."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

def _hash(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def _require(value: Any,name: str) -> Any:
    if value is None or value=="": raise ValueError(f"{name} is required")
    return value

def successor_candidate(*,break_id:str,prior_model:str,observation:Mapping[str,Any],
    failed_representation:str,distinction:str,discriminator:str,
    falsification_condition:str,evidence_refs:Sequence[str]=(),
    dependency_refs:Sequence[str]=(),self_audit_ref:str|None=None)->dict[str,Any]:
    _require(break_id,"break_id"); _require(prior_model,"prior_model")
    _require(failed_representation,"failed_representation"); _require(distinction,"distinction")
    _require(discriminator,"discriminator"); _require(falsification_condition,"falsification_condition")
    if not evidence_refs: raise ValueError("evidence_refs must contain at least one reference")
    candidate={"event_type":"SUCCESSOR_MODEL_CANDIDATE",
      "candidate_id":"candidate:"+_hash({"break_id":break_id,"prior_model":prior_model,"distinction":distinction,"discriminator":discriminator})[:24],
      "status":"PROPOSED","break_id":break_id,"prior_model":prior_model,"observation":dict(observation),
      "failed_representation":failed_representation,"distinction":distinction,"discriminator":discriminator,
      "falsification_condition":falsification_condition,"evidence_refs":list(evidence_refs),
      "dependency_refs":list(dependency_refs),"self_audit_ref":self_audit_ref,
      "authority":"CLAIM_LOCAL_ONLY","successor_model":None}
    candidate["candidate_hash"]=_hash(candidate)
    return candidate

def representation_pressure(*,exception_count:int,contradiction_count:int,repeated_failure_count:int,
    unresolved_boundary_count:int)->dict[str,Any]:
    counts={k:max(0,int(v)) for k,v in {
      "exception_count":exception_count,"contradiction_count":contradiction_count,
      "repeated_failure_count":repeated_failure_count,"unresolved_boundary_count":unresolved_boundary_count}.items()}
    return {"event_type":"REPRESENTATION_PRESSURE","components":counts,
      "interpretation":"REPEATED_FAILURE_OR_CONTRADICTION_MAY_WARRANT_REPRESENTATION_SEARCH",
      "score":None,"authority":"NONE"}

def audit_of_audit(*,audit_ref:str,findings:Sequence[Mapping[str,Any]],
    evidence_index:Mapping[str,Sequence[str]],test_index:Mapping[str,Sequence[str]])->dict[str,Any]:
    checks=[]
    for finding in findings:
        code=str(finding.get("code","")); evidence=list(finding.get("evidence",()))
        checks.append({"code":code,"evidence_traceable":bool(evidence) and all(ref in evidence_index for ref in evidence),
          "test_traceable":bool(test_index.get(code)),"status_claim":finding.get("status")})
    return {"event_type":"AUDIT_OF_AUDIT","audit_ref":_require(audit_ref,"audit_ref"),"checks":checks,
      "self_audit_ref":audit_ref,"authority":"CLAIM_LOCAL_ONLY","successor_model":None,
      "next_experiment":"Test the audit's own evidence and test mappings against independently observed repository state."}

def compare_candidates(candidates:Sequence[Mapping[str,Any]],observations:Sequence[Mapping[str,Any]])->dict[str,Any]:
    return {"event_type":"SUCCESSOR_MODEL_TEST_PLAN","candidate_ids":[c.get("candidate_id") for c in candidates],
      "observation_refs":[o.get("observation_ref") for o in observations],
      "tests":[{"candidate_id":c.get("candidate_id"),"discriminator":c.get("discriminator"),
        "falsification_condition":c.get("falsification_condition")} for c in candidates],
      "winner":None,"selection":"DEFERRED_UNTIL_DISCRIMINATING_OBSERVATION"}
