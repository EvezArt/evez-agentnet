#!/usr/bin/env python3
"""EVEZ Agentic OS assembly compiler.

Standard-library only. Consumes a repository capability inventory and an objective,
then emits a deterministic candidate OS manifest plus a human-readable plan.

This is a PLANNER, not a validator. Inferred repository capabilities remain PROPOSED.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_GRAPH=Path(__file__).resolve().parent/"data"/"github_inventory_2026-10-05.json"

ROLE_RULES=[
    ("research", re.compile(r"research|science|quantum|simulation|eigen|phenomen|math|model",re.I)),
    ("engineering", re.compile(r"engine|runtime|api|pipeline|factory|platform|code|claw|agent",re.I)),
    ("assurance", re.compile(r"evidence|spine|witness|ledger|proof|audit|invariant|forensic|guard|sentinel",re.I)),
    ("field", re.compile(r"android|device|station|terrain|mesh|net|sensor|telemetric|portal",re.I)),
    ("commerce", re.compile(r"commerce|store|product|revenue|profit|outreach|credit",re.I)),
    ("media", re.compile(r"audio|daw|voice|game|livestream|meme",re.I)),
]

CORE_BY_CAPABILITY={
    "evidence":["evez-event-spine","evez-evidence-runtime","evez-witness","evez-invariance-battery","evez-agentnet"],
    "agent_runtime":["openclaw-runtime","evez-openclaw-deploy","hermes-setup","evez-agentnet"],
    "research_science":["evez-phenomenologic","evez-sim","evez-benchmarks","evez-autonomous-ledger"],
    "field_device":["evez-openclaw-android","evez-device-portal","evez-meshnet"],
    "commerce":["evez-commerce","evez-outreach","evez-revenue-engine"],
}

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(v):
    return hashlib.sha256(canonical(v).encode()).hexdigest()

def load_graph(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema")!="evez.capability.graph.v1":
        raise ValueError("unexpected capability graph schema")
    return data

def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def score(repo, objective):
    text=" ".join([
        repo.get("name",""), repo.get("description",""),
        " ".join(repo.get("capabilities",[])),
    ]).lower()
    wanted=tokens(objective)
    overlap=sum(1 for t in wanted if len(t)>2 and t in text)
    cap_bonus=len(repo.get("capabilities",[]))
    core_bonus=8 if repo.get("name") in {n for v in CORE_BY_CAPABILITY.values() for n in v} else 0
    archive_penalty=10 if repo.get("archived") else 0
    general_penalty=3 if repo.get("capabilities")==["general"] else 0
    return overlap*5+min(cap_bonus,8)+core_bonus-archive_penalty-general_penalty

def select(graph, objective, limit=16):
    nodes=graph["nodes"]
    ranked=sorted(((score(n,objective),n) for n in nodes), key=lambda x:(x[0],-x[1].get("size_kb",0),x[1]["name"]), reverse=True)
    chosen=[]
    seen=set()
    for s,n in ranked:
        if n["name"] in seen or s<=0: continue
        chosen.append({
            "repo":n["full_name"],
            "capabilities":n["capabilities"],
            "score":s,
            "status":"PROPOSED",
            "basis":"repository-name/description heuristic"
        })
        seen.add(n["name"])
        if len(chosen)>=limit: break
    for cap, names in CORE_BY_CAPABILITY.items():
        for name in names:
            if any(x["repo"].endswith("/"+name) for x in chosen): continue
            node=next((n for n in nodes if n["name"]==name),None)
            if node:
                chosen.append({
                    "repo":node["full_name"],
                    "capabilities":node["capabilities"],
                    "score":"CORE_REQUIRED",
                    "status":"PROPOSED",
                    "basis":"assembly core registry"
                })
    return chosen

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("objective")
    ap.add_argument("--graph",default=str(DEFAULT_GRAPH))
    ap.add_argument("--id",default=None)
    ap.add_argument("--generation",type=int,default=0)
    ap.add_argument("--out",default="data/evez-foundry/candidate.json")
    args=ap.parse_args()
    graph=load_graph(args.graph)
    selected=select(graph,args.objective)
    osid=args.id or "evez-"+re.sub(r"[^a-z0-9]+","-",args.objective.lower()).strip("-")[:48]
    manifest={
        "$schema":"foundry/OS_MANIFEST.schema.json",
        "os_id":osid,
        "generation":args.generation,
        "objective":args.objective,
        "kernel":"evez-foundry-kernel-v0",
        "capabilities":sorted({c for x in selected for c in x["capabilities"]}),
        "agents":["SCOUT","HARVEST","COMPILER","EXPERIMENTER","RUNNER","WITNESS","CAIN","REPLICATOR","SYNTHESIZER","CARTOGRAPHER","BUILDER","CRITIC"],
        "tools":["Hermes","OpenClaw","EVEZ Spine"],
        "memory":["event-spine","candidate-state","artifact-index"],
        "tests":["boot","capability smoke","authority gate","evidence receipt","failure injection","replay"],
        "authority":{"maximum_autonomy":5},
        "evidence":{"spine":"evez-event-spine","promotion_ladder":["UNKNOWN","OBSERVED","EXECUTABLE","TESTED","REPRODUCED","VALIDATED","PROMOTED"]},
        "recovery":["preserve failure receipt","rollback isolated workspace","replay failed test","retain contradiction"],
        "selected_repositories":selected,
        "source_graph_digest":digest(graph),
        "planner_status":"PROPOSED",
        "doctrine":["CLAIMED != MEASURED != REPLICATED != EXPLAINED","PROVENANCE != TRUTH"],
    }
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(out),"os_id":osid,"selected":len(selected),"status":"PROPOSED","graph_digest":manifest["source_graph_digest"]},indent=2))

if __name__=="__main__":
    main()
