#!/usr/bin/env python3
"""Refresh a public GitHub repository inventory for the EVEZ Foundry.

Metadata and name/description heuristics are observations plus proposals.
The scanner never treats a repository name as proof of an implemented capability.
"""
from __future__ import annotations
import argparse, json, os, re, time
from urllib.request import Request, urlopen

API="https://api.github.com"

RULES=[
 ("evidence",r"spine|evidence|witness|ledger|proof|truth|forensic|invariant|lineage|audit|constitution|codex"),
 ("agent_runtime",r"agent|claw|molt|hermes|llm|cognition|omega|krnl|runtime|bot|conductor"),
 ("research_science",r"quantum|spectral|eigen|phenomen|research|science|model|simulation|sim(?:$|-)|manifold|telemetric|observatory|math"),
 ("field_device",r"android|device|station|terrain|mesh|net(?:$|-)|sensor|telemetric|portal"),
 ("commerce",r"commerce|store|product|revenue|profit|outreach|credit|service|landing"),
 ("security",r"guard|sentinel|threat|security|counterintel|disclosure|vault|watchdog|ban"),
 ("web_ui",r"dashboard|frontend|landing|vercel|github\.io|operator|portal|vcl|pwa"),
 ("media",r"audio|daw|voice|game|livestream|meme|song"),
 ("integration",r"api|bridge|router|bus|search|extension|factory|engine|pipeline|mesh"),
]

def get(path, token=None):
    headers={"Accept":"application/vnd.github+json","User-Agent":"EVEZ-Foundry/1.2","X-GitHub-Api-Version":"2022-11-28"}
    if token:
        headers["Authorization"]="Bearer "+token
    req=Request(API+path,headers=headers)
    with urlopen(req,timeout=30) as resp:
        return json.loads(resp.read().decode())

def proposed_capabilities(name, description):
    hay=(name+" "+(description or "")).lower()
    out=[label for label,pattern in RULES if re.search(pattern,hay)]
    return out or ["general"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--owner",default="EvezArt")
    ap.add_argument("--out",default="foundry/data/github_inventory.json")
    ap.add_argument("--max-pages",type=int,default=10)
    ap.add_argument("--include-private",action="store_true")
    args=ap.parse_args()
    if args.max_pages <= 0:
        ap.error("--max-pages must be a positive integer")

    token=os.getenv("GITHUB_TOKEN")
    repos=[]
    capped=False
    for page in range(1,args.max_pages+1):
        data=get(f"/users/{args.owner}/repos?type=owner&per_page=100&page={page}",token)
        if not isinstance(data,list):
            raise RuntimeError("GitHub response was not a repository list")
        visible=[r for r in data if args.include_private or not r.get("private",False)]
        repos.extend(visible)
        if len(data)<100:
            break
        if page == args.max_pages:
            capped=True
        time.sleep(.2)
    if capped:
        raise RuntimeError("repository inventory reached --max-pages cap; increase the cap or use a narrower source before publishing results")

    nodes=[]
    capability_index={}
    for r in repos:
        caps=proposed_capabilities(r["name"],r.get("description") or "")
        node={
          "id":"repo:"+r["name"],
          "type":"repository",
          "name":r["name"],
          "full_name":r["full_name"],
          "private":bool(r.get("private",False)),
          "description":r.get("description") or "",
          "archived":bool(r.get("archived")),
          "fork":bool(r.get("fork")),
          "size_kb":r.get("size") or 0,
          "default_branch":r.get("default_branch"),
          "capabilities":caps,
          "inference":"NAME_DESCRIPTION_HEURISTIC",
          "confidence":"PROPOSED",
          "observed":{
              "updated_at":r.get("updated_at"),
              "pushed_at":r.get("pushed_at"),
              "language":r.get("language")
          }
        }
        nodes.append(node)
        for cap in caps:
            capability_index.setdefault(cap,[]).append(node["id"])

    graph={
      "schema":"evez.capability.graph.v1",
      "source":"GitHub REST repository metadata",
      "owner":args.owner,
      "repository_count":len(nodes),
      "active_count":sum(1 for n in nodes if not n["archived"]),
      "archived_count":sum(1 for n in nodes if n["archived"]),
      "epistemic_status":"OBSERVED inventory; inferred capabilities are PROPOSED",
      "nodes":nodes,
      "capability_index":capability_index,
      "methodology":{
          "capability_inference":"repository name and description only",
          "not_claimed":"implementation quality, runtime health, security state, or reproducibility",
          "private_policy":"private repositories excluded unless --include-private is explicitly supplied",
          "next_probe":"inspect source trees, manifests, entrypoints, tests, workflows, and evidence artifacts"
      }
    }

    out=os.path.abspath(args.out)
    parent=os.path.dirname(out)
    if parent:
        os.makedirs(parent,exist_ok=True)
    with open(out,"w",encoding="utf-8") as f:
        json.dump(graph,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
      "repository_count":len(nodes),
      "active_count":graph["active_count"],
      "archived_count":graph["archived_count"],
      "out":out,
      "status":"OBSERVED + PROPOSED HEURISTICS"
    },indent=2))

if __name__=="__main__":
    main()
