#!/usr/bin/env python3
"""Inspect repository structure without publishing source contents."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com"
SOURCE_EXTS = {".py", ".js", ".mjs", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".sh"}
MANIFESTS = {"pyproject.toml", "requirements.txt", "package.json", "Cargo.toml", "go.mod", "pom.xml"}
ENTRY_PATTERNS = (
    re.compile(r"(^|/)(main|app|server|cli|run|index)\.[^/]+$", re.I),
    re.compile(r"(^|/)(start|launch|deploy)[^/]*\.(py|js|mjs|sh)$", re.I),
)
SYMBOL_PATTERNS = (
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)"),
)

def api_get(path, token=None):
    headers = {"Accept":"application/vnd.github+json","User-Agent":"EVEZ-Foundry/1.1","X-GitHub-Api-Version":"2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(API + path, headers=headers), timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))

def symbols(text):
    out = []
    for line in text.splitlines():
        for pattern in SYMBOL_PATTERNS:
            match = pattern.search(line)
            if match:
                out.append(match.group(1))
    return sorted(set(out))[:100]

def inspect(repo, max_sources, token):
    metadata = api_get(f"/repos/{repo}", token)
    branch = metadata.get("default_branch") or "main"
    tree = api_get(f"/repos/{repo}/git/trees/{branch}?recursive=1", token)
    items = tree.get("tree", [])
    files = [x for x in items if x.get("type") == "blob"]
    selected = [x for x in files if Path(x.get("path","")).suffix.lower() in SOURCE_EXTS]
    selected = sorted(selected, key=lambda x:(len(x.get("path","")),x.get("path","")))[:max_sources]

    records = []
    for item in files:
        path = item.get("path","")
        lower = path.lower()
        name = Path(path).name
        if name == "README.md": kind = "readme"
        elif name in MANIFESTS: kind = "manifest"
        elif ".github/workflows/" in lower: kind = "workflow"
        elif re.search(r"(^|/)(tests?|specs?)(/|\.)", lower): kind = "test"
        elif Path(path).suffix.lower() in SOURCE_EXTS: kind = "source"
        else: kind = "other"
        records.append({
            "path": path,
            "size": item.get("size",0),
            "sha": item.get("sha"),
            "kind": kind,
            "entrypoint_candidate": any(p.search(path) for p in ENTRY_PATTERNS),
        })

    detail = {}
    for item in selected:
        path = item["path"]
        try:
            raw = api_get(f"/repos/{repo}/contents/{path}?ref={branch}", token)
            encoded = (raw.get("content") or "").replace("\n","")
            if not encoded:
                continue
            data = base64.b64decode(encoded).decode("utf-8","replace")
            detail[path] = {
                "sha": item.get("sha"),
                "content_digest": hashlib.sha256(data.encode("utf-8")).hexdigest(),
                "symbols": symbols(data),
            }
        except Exception as exc:
            detail[path] = {"error": type(exc).__name__}

    return {
        "schema":"evez.repository.inspection.v1",
        "repository":repo,
        "default_branch":branch,
        "head_tree":tree.get("sha"),
        "file_count":len(files),
        "source_files_considered":len(selected),
        "manifests":sorted(r["path"] for r in records if r["kind"]=="manifest")[:100],
        "tests":sorted(r["path"] for r in records if r["kind"]=="test")[:200],
        "workflows":sorted(r["path"] for r in records if r["kind"]=="workflow")[:200],
        "entrypoint_candidates":sorted(r["path"] for r in records if r["entrypoint_candidate"])[:100],
        "files":records,
        "source_details":detail,
        "epistemic_status":"OBSERVED_METADATA_PLUS_SYMBOL_EXTRACTION",
        "not_claimed":["runtime health","security","reproducibility","implementation correctness"],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repository")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-sources", type=int, default=80)
    args = ap.parse_args()
    result = inspect(args.repository, args.max_sources, os.getenv("GITHUB_TOKEN"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({
        "repository":args.repository,
        "files":result["file_count"],
        "manifests":len(result["manifests"]),
        "tests":len(result["tests"]),
        "workflows":len(result["workflows"]),
        "entrypoints":len(result["entrypoint_candidates"]),
        "status":result["epistemic_status"],
        "out":str(out),
    }, indent=2))

if __name__ == "__main__":
    main()
