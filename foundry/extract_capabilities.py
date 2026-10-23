#!/usr/bin/env python3
"""Convert repository inspection records into evidence-backed capability records."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

ROLE_PATTERNS = {
    "research": r"research|science|quantum|simulation|eigen|phenomen|math|model",
    "engineering": r"engine|runtime|api|pipeline|factory|platform|code|claw|agent",
    "assurance": r"evidence|spine|witness|ledger|proof|audit|invariant|forensic|guard|sentinel",
    "field": r"android|device|station|terrain|mesh|sensor|telemetric|portal",
    "commerce": r"commerce|store|product|revenue|profit|outreach|credit",
}

def evidence_id(repo: str, capability: str, evidence: object) -> str:
    raw = json.dumps({"repo": repo, "capability": capability, "evidence": evidence}, sort_keys=True, separators=(",", ":"))
    return "cap-" + hashlib.sha256(raw.encode()).hexdigest()[:20]

def classify(item: dict, source_details: dict) -> list[dict]:
    text = " ".join([
        item.get("repository", ""),
        " ".join(item.get("manifests", [])),
        " ".join(item.get("entrypoint_candidates", [])),
        " ".join(item.get("tests", [])),
        " ".join(source_details),
    ]).lower()
    roles = [role for role, pattern in ROLE_PATTERNS.items() if re.search(pattern, text)]
    if not roles:
        roles = ["general"]
    evidence = {
        "source_repository": item.get("repository"),
        "manifests": item.get("manifests", [])[:50],
        "tests": item.get("tests", [])[:50],
        "entrypoints": item.get("entrypoint_candidates", [])[:50],
        "source_files": list(source_details)[:80],
    }
    status = "OBSERVED" if item.get("source_details") else "UNKNOWN"
    out = []
    for role in roles:
        out.append({
            "capability_id": evidence_id(item["repository"], role, evidence),
            "name": role,
            "repository": item["repository"],
            "state": status,
            "confidence": "PROPOSED",
            "evidence": evidence,
            "interfaces": [],
            "dependencies": [],
            "side_effects": "UNKNOWN",
            "reproducibility": "UNKNOWN",
            "notes": "Role is inferred from observed repository structure and symbol/file names; runtime correctness is not established.",
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inspection")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.inspection).read_text(encoding="utf-8"))
    records = classify(data, data.get("source_details", {}))
    graph = {
        "schema": "evez.capability.records.v1",
        "repository": data.get("repository"),
        "records": records,
        "doctrine": ["CLAIMED != MEASURED != REPLICATED != EXPLAINED", "PROVENANCE != TRUTH"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"repository": data.get("repository"), "capabilities": len(records), "out": str(out)}, indent=2))

if __name__ == "__main__":
    main()
