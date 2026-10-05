#!/usr/bin/env python3
"""Inspect repository structure without publishing source contents.

The inspector records file metadata, likely entrypoints, dependency manifests,
tests, workflows, and symbol names. It does not store raw file contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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

def api_get(path: str, token: str | None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "EVEZ-Foundry/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(API + path, headers=headers)
    with urlopen(req, timeout=40) as resp:
        value = json.loads(resp.read().decode("utf-8"))
    return value

def source_symbols(content: str) -> list[str]:
    symbols = []
    for line in content.splitlines():
        for pattern in SYMBOL_PATTERNS:
            match = pattern.search(line)
            if match:
                symbols.append(match.group(1))
    return sorted(set(symbols))[:100]

def inspect(repo: str, max_sources: int, token: str | None) -> dict:
    tree = api_get(f"/repos/{repo}/git/trees/HEAD?recursive=1", token)
    items = tree.get("tree", [])
    files = [x for x in items if x.get("type") == "blob"]
    selected = [x for x in files if Path(x.get("path", "")).suffix.lower() in SOURCE_EXTS]
    selected = sorted(selected, key=lambda x: (len(x.get("path", "")), x.get("path", "")))[:max_sources]

    records = []
    for item in files:
        path = item.get("path", "")
        name = Path(path).name
        lower = path.lower()
        kind = "other"
        if name == "README.md":
            kind = "readme"
        elif name in MANIFESTS:
            kind = "manifest"
        elif ".github/workflows/" in lower:
            kind = "workflow"
        elif "/test" in lower or lower.startswith("test") or "tests/" in lower:
            kind = "test"
        elif Path(path).suffix.lower() in SOURCE_EXTS:
            kind = "source"

        records.append({
            "path": path,
            "size": item.get("size", 0),
            "sha": item.get("sha"),
            "kind": kind,
            "entrypoint_candidate": any(p.search(path) for p in ENTRY_PATTERNS),
        })

    detail = {}
    for item in selected:
        path = item["path"]
        try:
            raw = api_get(f"/repos/{repo}/contents/{path}", token)
            encoded = raw.get("content", "").replace("\n", "")
            if not encoded:
                continue
            import base64
            data = base64.b64decode(encoded).decode("utf-8", "replace")
            detail[path] = {
                "sha": item.get("sha"),
                "content_digest": hashlib.sha256(data.encode("utf-8")).hexdigest(),
                "symbols": source_symbols(data),
            }
        except Exception as exc:
            detail[path] = {"error": type(exc).__name__}

    manifests = sorted(
        r["path"] for r in records if r["kind"] == "manifest"
    )
    tests = sorted(
        r["path"] for r in records if r["kind"] == "test"
    )
    workflows = sorted(
        r["path"] for r in records if r["kind"] == "workflow"
    )
    entries = sorted(
        r["path"] for r in records if r["entrypoint_candidate"]
    )

    return {
        "schema": "evez.repository.inspection.v1",
        "repository": repo,
        "head_tree": tree.get("sha"),
        "file_count": len(files),
        "source_files_considered": len(selected),
        "manifests": manifests[:100],
        "tests": tests[:200],
        "workflows": workflows[:200],
        "entrypoint_candidates": entries[:100],
        "files": records,
        "source_details": detail,
        "epistemic_status": "OBSERVED_METADATA_PLUS_SYMBOL_EXTRACTION",
        "not_claimed": [
            "runtime health",
            "security",
            "reproducibility",
            "implementation correctness",
        ],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repository", help="owner/name")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-sources", type=int, default=80)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    result = inspect(args.repository, args.max_sources, token)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "repository": args.repository,
        "files": result["file_count"],
        "manifests": len(result["manifests"]),
        "tests": len(result["tests"]),
        "workflows": len(result["workflows"]),
        "entrypoints": len(result["entrypoint_candidates"]),
        "status": result["epistemic_status"],
        "out": str(out),
    }, indent=2))

if __name__ == "__main__":
    main()
