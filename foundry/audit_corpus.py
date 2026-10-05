#!/usr/bin/env python3
"""Read-only corpus audit for EVEZ Foundry.

Produces a risk/cleanup queue from public GitHub metadata and top-level trees.
No deletion, mutation, secret rotation, merge, deploy, or external communication.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com"

def get(path: str, token: str | None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "EVEZ-Foundry-Audit/1.0", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(API + path, headers=headers)
    with urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))

def flag_paths(paths: list[str]) -> dict:
    joined = "\n".join(paths).lower()
    return {
        "virtualenv_candidate": any("/.venv/" in ("/"+p.lower()+"/") or p.lower().startswith(".venv/") for p in paths),
        "dependency_artifact_candidate": any("/node_modules/" in ("/"+p.lower()+"/") for p in paths),
        "build_artifact_candidate": any(re.search(r"(^|/)(dist|build|coverage)/", p.lower()) for p in paths),
        "secret_filename_candidate": any(re.search(r"(^|/)(\.env$|.*pat.*|.*token.*|.*secret.*|.*credential.*)", p.lower()) for p in paths),
        "mirror_candidate": any(re.search(r"(^|/)(mirror|mirrors|backup|ecosystem|repos|repositories)/?", p.lower()) for p in paths),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="EvezArt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--sleep", type=float, default=0.1)
    args = ap.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    repos = []
    for page in range(1, args.max_pages + 1):
        batch = get(f"/users/{args.owner}/repos?type=owner&per_page=100&page={page}", token)
        repos.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(args.sleep)

    findings = []
    for repo in repos:
        full = repo["full_name"]
        tree = get(f"/repos/{full}/git/trees/{repo.get("default_branch", "main")}?recursive=1", token)
        paths = [x.get("path", "") for x in tree.get("tree", []) if x.get("type") == "blob"]
        flags = flag_paths(paths)
        risk = []
        if repo.get("size", 0) > 100000:
            risk.append("LARGE_REPOSITORY")
        if repo.get("archived"):
            risk.append("ARCHIVED")
        for key, value in flags.items():
            if value:
                risk.append(key.upper())
        if repo.get("default_branch") not in ("main", "trunk", "master"):
            risk.append("NONSTANDARD_DEFAULT_BRANCH")
        findings.append({
            "repository": full,
            "archived": bool(repo.get("archived")),
            "size_kb": repo.get("size", 0),
            "default_branch": repo.get("default_branch"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "file_count": len(paths),
            "flags": flags,
            "risk_classes": sorted(set(risk)),
            "status": "OBSERVED",
        })

    report = {
        "schema": "evez.corpus.audit.v1",
        "owner": args.owner,
        "repository_count": len(findings),
        "findings": findings,
        "doctrine": ["read-only by default", "never print credential values", "UNKNOWN until evidence supports a stronger state"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {}
    for row in findings:
        for risk in row["risk_classes"]:
            counts[risk] = counts.get(risk, 0) + 1
    print(json.dumps({"repositories": len(findings), "risk_counts": counts, "out": str(out)}, indent=2))

if __name__ == "__main__":
    main()
