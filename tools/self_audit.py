#!/usr/bin/env python3
"""Dependency-free audit of EVEZ own semantic claims."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT_FILES = {"module":"evez_unacknowledged.py","schema":"schemas/evez-unacknowledged-event.schema.json","tests":"tests/test_unacknowledged_layer.py","docs":"docs/UNACKNOWLEDGED_LAYER.md","ci":".github/workflows/unacknowledged-layer.yml"}

def _read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")

def finding(code: str, status: str, claim: str, evidence: list[str], *, consequence: str = "", next_experiment: str = "") -> dict[str, Any]:
    return {"event_type":"SELF_AUDIT_FINDING","code":code,"status":status,"claim":claim,"evidence":evidence,"consequence":consequence,"next_experiment":next_experiment}

def audit(root: str | Path) -> list[dict[str, Any]]:
    root=Path(root)
    module=_read(root,ROOT_FILES["module"]); schema=_read(root,ROOT_FILES["schema"]); docs=_read(root,ROOT_FILES["docs"]); ci=_read(root,ROOT_FILES["ci"])
    out=[]
    out.append(finding("CHAIN_CONTENT_ORDER","ENFORCED" if "body[\"parent_hash\"] = parent_hash" in module and "body[\"content_hash\"] = sha256(body)" in module else "GAP","content hash covers parent hash before event hash.","[make_event]"))
    out.append(finding("TIMESTAMP_ASSERTION","ENFORCED" if '"format-assertion": true' in schema and "RFC 3339" in module else "GAP","timestamp syntax is asserted by schema and runtime.","[schema,make_event]"))
    out.append(finding("CHAIN_SHAPE","ENFORCED" if "not isinstance(event, dict)" in module else "GAP","non-object ledger lines are rejected.","[verify_chain]"))
    out.append(finding("NULL_OBSERVATION","ENFORCED" if "MISSING = object()" in module and "observed is not MISSING" in module else "GAP","explicit null outcomes remain distinguishable from omission.","[prediction]"))
    out.append(finding("VERIFICATION_ORDER","ENFORCED" if '"OBSERVE", "VERIFY"' in module and "verification_evidence" in module else "GAP","verification requires observation and evidence.","[handshake]"))
    out.append(finding("SELF_AUDIT_CI","ENFORCED" if "test_self_audit.py" in ci else "GAP","self-audit is wired into CI.","[workflow]"))
    out.append(finding("ONTOLOGY_DUPLICATION","REVIEW","negative-space terminology needs an explicit relationship to the existing frontier model.","[docs/UNACKNOWLEDGED_LAYER.md]","two definitions can silently diverge","map fields and lifecycle states"))
    out.append(finding("POLICY_ENFORCEMENT","ONTOLOGY_BREAK_CANDIDATE","normative documentation is not automatically runtime enforcement.","[docs/UNACKNOWLEDGED_LAYER.md]","documentation can outrun executable guarantees","trace each normative sentence to code and CI"))
    return out

def main() -> None:
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("root",nargs="?",default="."); args=p.parse_args()
    print(json.dumps(audit(args.root),indent=2,sort_keys=True))

if __name__=="__main__": main()
