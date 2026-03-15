#!/usr/bin/env python3
"""
Cross-Pollinator — spreads knowledge and improvements across repos.
When a pattern/fix works in one repo, applies it to others.
Evaluates new libraries/techniques for all repos.
Maintains known-good patterns and creates multi-repo improvement PRs.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.knowledge.cross_pollinate")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "EvezArt"

PATTERNS_PATH = Path("knowledge/patterns.json")
CAPABILITIES_PATH = Path("knowledge/capabilities.json")
GRAPH_PATH = Path("knowledge/graph.json")

ALL_REPOS = [
    "evez-os",
    "evez-agentnet",
    "evez-autonomous-ledger",
    "agentvault",
    "evez-meme-bus",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_patterns() -> dict:
    if PATTERNS_PATH.exists():
        return json.loads(PATTERNS_PATH.read_text())
    return {"patterns": [], "updated_at": now_iso()}


def _save_patterns(data: dict):
    data["updated_at"] = now_iso()
    PATTERNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PATTERNS_PATH.write_text(json.dumps(data, indent=2))


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _gh_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "Content-Type": "application/json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


# ── Pattern extraction ──

def extract_local_patterns() -> list:
    """Extract known-good patterns from the current repo."""
    patterns = []
    root = Path(".")

    for py_file in root.rglob("*.py"):
        if any(p.startswith(".") or p == "__pycache__" for p in py_file.parts):
            continue
        try:
            content = py_file.read_text(errors="ignore")
            module = str(py_file)

            # Pattern: fault-tolerant API calls
            if "try:" in content and "except" in content and ("urllib" in content or "requests" in content):
                patterns.append({
                    "name": "fault_tolerant_api",
                    "description": "Try/except around external API calls with graceful fallback",
                    "source_repo": "evez-agentnet",
                    "source_module": module,
                    "category": "reliability",
                })

            # Pattern: append-only JSONL logging
            if "jsonl" in content.lower() or ('.write(json.dumps(' in content and '+ "\\n"' in content):
                patterns.append({
                    "name": "append_only_jsonl",
                    "description": "Append-only JSONL for provenance and audit logging",
                    "source_repo": "evez-agentnet",
                    "source_module": module,
                    "category": "provenance",
                })

            # Pattern: env var with graceful fallback
            if 'os.environ.get(' in content:
                patterns.append({
                    "name": "env_graceful_fallback",
                    "description": "Environment variable reading with default fallback (no crash on missing)",
                    "source_repo": "evez-agentnet",
                    "source_module": module,
                    "category": "fault_tolerance",
                })

            # Pattern: hash-based integrity
            if "hashlib" in content and ("sha256" in content or "md5" in content):
                patterns.append({
                    "name": "hash_integrity",
                    "description": "Hashlib-based integrity checking for provenance chains",
                    "source_repo": "evez-agentnet",
                    "source_module": module,
                    "category": "integrity",
                })

            # Pattern: dataclass-based models
            if "from dataclasses import" in content and "@dataclass" in content:
                patterns.append({
                    "name": "dataclass_models",
                    "description": "Dataclass-based typed data models for structured state",
                    "source_repo": "evez-agentnet",
                    "source_module": module,
                    "category": "code_quality",
                })

        except Exception:
            pass

    # Deduplicate patterns by name
    seen = set()
    unique = []
    for p in patterns:
        if p["name"] not in seen:
            seen.add(p["name"])
            p["discovered_at"] = now_iso()
            unique.append(p)

    return unique


# ── Cross-repo evaluation ──

def _check_repo_has_pattern(repo: str, pattern_name: str) -> bool:
    """Check if a remote repo already uses a pattern (heuristic via file tree)."""
    if not GITHUB_TOKEN:
        return True  # Assume yes if we can't check

    try:
        # Check repo README or key files for pattern indicators
        url = f"https://api.github.com/repos/{OWNER}/{repo}/git/trees/main?recursive=1"
        req = urllib.request.Request(url, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        paths = [item["path"] for item in data.get("tree", [])]

        if pattern_name == "append_only_jsonl":
            return any("spine" in p or "jsonl" in p for p in paths)
        if pattern_name == "hash_integrity":
            return any("spine" in p or "provenance" in p for p in paths)
        if pattern_name == "dataclass_models":
            return any("model" in p.lower() or "types" in p.lower() for p in paths)

        return False  # Unknown pattern, assume not present
    except Exception:
        return True  # On error, don't spam issues


def evaluate_patterns_across_repos(patterns: list) -> list:
    """Evaluate which patterns should be applied to which repos."""
    recommendations = []

    for pattern in patterns:
        source_repo = pattern.get("source_repo", "")
        for repo in ALL_REPOS:
            if repo == source_repo:
                continue

            has_pattern = _check_repo_has_pattern(repo, pattern["name"])
            if not has_pattern:
                recommendations.append({
                    "pattern": pattern["name"],
                    "description": pattern["description"],
                    "category": pattern["category"],
                    "source_repo": source_repo,
                    "target_repo": repo,
                    "status": "recommended",
                    "evaluated_at": now_iso(),
                })

    return recommendations


# ── Issue creation for cross-pollination ──

def _create_cross_pollination_issue(recommendation: dict) -> bool:
    """Create a GitHub issue recommending a pattern be applied."""
    if not GITHUB_TOKEN:
        log.info(f"  [DRY RUN] Would recommend {recommendation['pattern']} for {recommendation['target_repo']}")
        return False

    try:
        url = f"https://api.github.com/repos/{OWNER}/{recommendation['target_repo']}/issues"
        body = (
            f"**Cross-Pollination Recommendation**\n\n"
            f"**Pattern:** {recommendation['pattern']}\n"
            f"**Description:** {recommendation['description']}\n"
            f"**Category:** {recommendation['category']}\n"
            f"**Source:** {recommendation['source_repo']}\n\n"
            f"This pattern has been proven in `{recommendation['source_repo']}` and could benefit this repo.\n\n"
            f"*Auto-generated by knowledge cross-pollinator. Requires human review.*"
        )
        payload = json.dumps({
            "title": f"[CROSS-POLLINATE] Apply {recommendation['pattern']} pattern",
            "body": body,
            "labels": ["cross-pollination", "auto-generated"],
        }).encode()
        req = urllib.request.Request(url, data=payload, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        log.warning(f"Cross-pollination issue failed for {recommendation['target_repo']}: {e}")
        return False


# ── Discovery evaluation across repos ──

def evaluate_discoveries_across_repos() -> list:
    """Check if new discoveries/techniques are applicable to all repos."""
    graph = _load_json(GRAPH_PATH)
    recommendations = []

    for concept, data in graph.get("concepts", {}).items():
        repos_with = set(data.get("repos", []))
        repos_without = set(ALL_REPOS) - repos_with

        if repos_with and repos_without and len(data.get("discoveries", [])) >= 2:
            for repo in repos_without:
                recommendations.append({
                    "pattern": f"concept_{concept}",
                    "description": f"Knowledge concept '{concept}' is used in {', '.join(repos_with)} but not in {repo}",
                    "category": "knowledge_gap",
                    "source_repo": list(repos_with)[0],
                    "target_repo": repo,
                    "status": "recommended",
                    "evaluated_at": now_iso(),
                })

    return recommendations[:5]


# ── Main entry point ──

def run() -> dict:
    """Execute cross-pollination analysis and create recommendations."""
    log.info(f"Cross-Pollinator starting — {now_iso()}")

    # Extract patterns from local repo
    patterns = extract_local_patterns()
    log.info(f"  Extracted {len(patterns)} patterns from local repo")

    # Evaluate patterns across repos
    pattern_recs = evaluate_patterns_across_repos(patterns)
    log.info(f"  Pattern recommendations: {len(pattern_recs)}")

    # Evaluate discoveries across repos
    discovery_recs = evaluate_discoveries_across_repos()
    log.info(f"  Discovery recommendations: {len(discovery_recs)}")

    all_recs = pattern_recs + discovery_recs

    # Create issues for top recommendations
    issues_created = 0
    for rec in all_recs[:5]:  # Max 5 issues per run
        if _create_cross_pollination_issue(rec):
            issues_created += 1
        log.info(f"  [{rec['status']}] {rec['pattern']} -> {rec['target_repo']}")

    # Save patterns
    patterns_data = _load_patterns()
    # Merge new patterns with existing
    existing_names = {p["name"] for p in patterns_data.get("patterns", [])}
    for p in patterns:
        if p["name"] not in existing_names:
            patterns_data.setdefault("patterns", []).append(p)
    _save_patterns(patterns_data)

    stats = {
        "patterns_extracted": len(patterns),
        "pattern_recommendations": len(pattern_recs),
        "discovery_recommendations": len(discovery_recs),
        "issues_created": issues_created,
    }

    log.info(f"  Stats: {stats}")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = run()
    print(json.dumps(stats, indent=2))
