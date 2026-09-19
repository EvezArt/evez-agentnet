"""Identity/authority kernel for EVEZ.

'LORD' is a system-design role, not a claim of supernatural status.
Authority is scoped to an explicitly identified principal, action, evidence,
and authorization. No global authority is emitted.
"""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping,Sequence

def _hash(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def identity_record(*,identity:str,continuity_refs:Sequence[str],source_layer:str="REAL")->dict[str,Any]:
    if not identity: raise ValueError("identity is required")
    if not continuity_refs: raise ValueError("continuity_refs must not be empty")
    r={"event_type":"IDENTITY_CONTINUITY","identity":identity,
       "identity_status":"HYPOTHESIS","continuity_refs":list(continuity_refs),
       "source_layer":source_layer,"authority":"CLAIM_LOCAL_ONLY"}
    r["content_hash"]=_hash(r)
    return r

def lord_directive(*,principal:str,objective:str,action:str,
                   authorization_ref:str,evidence_refs:Sequence[str],
                   observed_effect_ref:str|None=None)->dict[str,Any]:
    if not principal or not objective or not action: raise ValueError("principal, objective, and action are required")
    if not authorization_ref: raise ValueError("authorization_ref is required")
    if not evidence_refs: raise ValueError("evidence_refs must not be empty")
    return {
      "event_type":"SCOPED_DIRECTIVE","principal":principal,"objective":objective,
      "action":action,"authorization_ref":authorization_ref,
      "evidence_refs":list(evidence_refs),"observed_effect_ref":observed_effect_ref,
      "status":"AUTHORIZED_PENDING_EFFECT" if observed_effect_ref is None else "EFFECT_OBSERVED",
      "authority":"SCOPED_NOT_GLOBAL",
    }

def succession_rule(*,old_model:str,new_candidate:str,tests:Sequence[str],
                    evidence_refs:Sequence[str])->dict[str,Any]:
    if not tests or not evidence_refs: raise ValueError("tests and evidence_refs are required")
    return {"event_type":"MODEL_SUCCESSION","ancestor":old_model,
      "candidate":new_candidate,"tests":list(tests),"evidence_refs":list(evidence_refs),
      "promotion":"DEFERRED_UNTIL_TESTS_DISCRIMINATE","authority":"NONE"}
