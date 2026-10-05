#!/usr/bin/env python3
"""Refresh a public GitHub repository inventory for the EVEZ Foundry.

Uses only the GitHub REST API and records metadata, not source contents.
Set GITHUB_TOKEN for higher rate limits. Never writes credentials to output.
"""
from __future__ import annotations
import argparse,json,os,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

API="https://api.github.com"

def get(path,token=None):
    h={"Accept":"application/vnd.github+json","User-Agent":"EVEZ-Foundry/1.0","X-GitHub-Api-Version":"2022-11-28"}
    if token: h["Authorization"]="Bearer "+token
    req=Request(API+path,headers=h)
    with urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--owner",default="EvezArt")
    ap.add_argument("--out",default="foundry/data/github_inventory.json")
    ap.add_argument("--max-pages",type=int,default=10)
    args=ap.parse_args()
    token=os.getenv("GITHUB_TOKEN")
    repos=[]
    for page in range(1,args.max_pages+1):
        data=get(f"/users/{args.owner}/repos?type=owner&per_page=100&page={page}",token)
        if not isinstance(data,list): raise RuntimeError("GitHub response was not a repository list")
        repos.extend(data)
        if len(data)<100: break
        time.sleep(.2)
    nodes=[]
    for r in repos:
        nodes.append({
            "id":"repo:"+r["name"],
            "type":"repository",
            "name":r["name"],
            "full_name":r["full_name"],
            "description":r.get("description") or "",
            "archived":bool(r.get("archived")),
            "fork":bool(r.get("fork")),
            "size_kb":r.get("size") or 0,
            "default_branch":r.get("default_branch") or "main",
            "capabilities":["general"],
            "inference":"REFRESHED_METADATA",
            "confidence":"UNKNOWN",
            "observed":{"updated_at":r.get("updated_at"),"pushed_at":r.get("pushed_at"),"language":r.get("language")}
        })
    graph={
      "schema":"evez.capability.graph.v1",
      "source":"GitHub REST repository metadata",
      "owner":args.owner,
      "repository_count":len(nodes),
      "epistemic_status":"OBSERVED metadata; capabilities UNKNOWN until source inspection",
      "nodes":nodes,
      "methodology":{"source":"repository metadata only","next_probe":"inspect tree/manifests/entrypoints/tests/workflows"}
    }
    p=os.path.abspath(args.out)
    os.makedirs(os.path.dirname(p),exist_ok=True)
    open(p,"w",encoding="utf-8").write(json.dumps(graph,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"repository_count":len(nodes),"out":p,"capabilities":"UNKNOWN until inspection"},indent=2))

if __name__=="__main__":
    main()
