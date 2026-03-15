#!/usr/bin/env python3
"""
Capability Registry — tracks what the system can do.
Scans repos for: API endpoints, CLI commands, agent capabilities, skills.
Maintains a live registry and identifies capability gaps.
"""
import os
import json
import logging
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.knowledge.capabilities")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "EvezArt"

CAPABILITIES_PATH = Path("knowledge/capabilities.json")

# Known repos and their expected capability types
REPO_SCAN_CONFIG = {
    "evez-os": {"types": ["kernel", "service", "cli"], "languages": ["python", "shell"]},
    "evez-agentnet": {"types": ["agent", "scanner", "generator", "skill"], "languages": ["python"]},
    "evez-autonomous-ledger": {"types": ["governance", "audit"], "languages": ["python", "markdown"]},
    "agentvault": {"types": ["security", "vault"], "languages": ["python"]},
    "evez-meme-bus": {"types": ["content", "social"], "languages": ["python"]},
}

# Capabilities the system should have but might not yet
EXPECTED_CAPABILITIES = [
    {"name": "self_repair", "description": "Automatically detect and fix broken components"},
    {"name": "self_deploy", "description": "Deploy updates autonomously with rollback"},
    {"name": "income_generation", "description": "Generate revenue through content/predictions"},
    {"name": "knowledge_expansion", "description": "Continuously learn from external sources"},
    {"name": "multi_agent_coordination", "description": "Coordinate multiple agents on tasks"},
    {"name": "browser_automation", "description": "Automate web interactions"},
    {"name": "credential_management", "description": "Securely manage API keys and secrets"},
    {"name": "provenance_tracking", "description": "Track all actions with hash-chain integrity"},
    {"name": "reputation_staking", "description": "Gate capabilities by agent reputation scores"},
    {"name": "meta_learning", "description": "Learn from own performance and improve"},
    {"name": "cross_repo_sync", "description": "Synchronize patterns and fixes across repos"},
    {"name": "semantic_search", "description": "Search knowledge base semantically"},
    {"name": "skill_synthesis", "description": "Generate new skills from learned knowledge"},
    {"name": "quantum_optimization", "description": "Quantum-inspired resource optimization"},
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_capabilities() -> dict:
    if CAPABILITIES_PATH.exists():
        return json.loads(CAPABILITIES_PATH.read_text())
    return {"capabilities": [], "gaps": [], "updated_at": now_iso()}


def _save_capabilities(registry: dict):
    registry["updated_at"] = now_iso()
    CAPABILITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAPABILITIES_PATH.write_text(json.dumps(registry, indent=2))


# ── Local repo scanner ──

def scan_local_repo(repo_path: str = ".") -> list:
    """Scan a local repo for capabilities (Python modules with run() or main())."""
    capabilities = []
    root = Path(repo_path)

    for py_file in root.rglob("*.py"):
        # Skip hidden dirs and __pycache__
        if any(p.startswith(".") or p == "__pycache__" for p in py_file.parts):
            continue

        try:
            content = py_file.read_text(errors="ignore")
            module_path = str(py_file.relative_to(root))

            # Detect capability type
            cap_type = "module"
            if "def run(" in content:
                cap_type = "agent"
            elif "def main(" in content:
                cap_type = "cli"
            elif "class " in content and "Agent" in content:
                cap_type = "agent"
            elif "/api/" in content or "endpoint" in content.lower():
                cap_type = "api"

            # Extract name from module
            name = py_file.stem
            if name.startswith("__"):
                continue

            # Extract docstring
            doc = ""
            if '"""' in content:
                start = content.index('"""') + 3
                end = content.index('"""', start)
                doc = content[start:end].strip()[:200]

            capabilities.append({
                "name": name,
                "repo": root.name,
                "module": module_path,
                "type": cap_type,
                "description": doc,
                "status": "active",
                "last_used": None,
                "effectiveness_score": None,
            })
        except Exception as e:
            log.debug(f"Scan error {py_file}: {e}")

    return capabilities


# ── Skill scanner ──

def scan_skills() -> list:
    """Scan for skill definitions (SKILL.md files)."""
    capabilities = []
    skill_dirs = [
        Path(".claude/skills"),
        Path("skills/generated"),
    ]

    for skill_root in skill_dirs:
        if not skill_root.exists():
            continue
        for skill_md in skill_root.rglob("SKILL.md"):
            try:
                content = skill_md.read_text()
                name = skill_md.parent.name
                # Extract description from frontmatter or first paragraph
                desc = ""
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip()
                        break
                if not desc:
                    for line in lines:
                        if line and not line.startswith("#") and not line.startswith("-"):
                            desc = line.strip()[:200]
                            break

                capabilities.append({
                    "name": f"skill_{name}",
                    "repo": "evez-agentnet",
                    "module": str(skill_md.relative_to(".")),
                    "type": "skill",
                    "description": desc,
                    "status": "active" if "generated" not in str(skill_md) else "draft",
                    "last_used": None,
                    "effectiveness_score": None,
                })
            except Exception as e:
                log.debug(f"Skill scan error {skill_md}: {e}")

    return capabilities


# ── GitHub API scanner (remote repos) ──

def scan_remote_repo(repo: str) -> list:
    """Scan a remote GitHub repo's tree for capabilities."""
    capabilities = []
    if not GITHUB_TOKEN:
        return capabilities

    try:
        url = f"https://api.github.com/repos/{OWNER}/{repo}/git/trees/main?recursive=1"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        for item in data.get("tree", []):
            path = item.get("path", "")
            if not path.endswith(".py") or path.startswith("."):
                continue
            name = Path(path).stem
            if name.startswith("__"):
                continue

            cap_type = "module"
            if "agent" in path.lower():
                cap_type = "agent"
            elif "test" in path.lower():
                continue  # Skip tests

            capabilities.append({
                "name": name,
                "repo": repo,
                "module": path,
                "type": cap_type,
                "status": "active",
                "last_used": None,
                "effectiveness_score": None,
            })
    except Exception as e:
        log.warning(f"Remote scan of {repo} failed: {e}")

    return capabilities


# ── Gap analysis ──

def _identify_gaps(capabilities: list) -> list:
    """Identify capability gaps: things the system should do but can't."""
    existing_names = {c["name"].lower() for c in capabilities}
    existing_types = {c["type"] for c in capabilities}
    existing_descriptions = " ".join(c.get("description", "") for c in capabilities).lower()

    gaps = []
    for expected in EXPECTED_CAPABILITIES:
        name = expected["name"]
        desc = expected["description"].lower()

        # Check if capability exists
        has_it = (
            name.lower() in existing_names or
            any(name.lower().replace("_", "") in n.replace("_", "") for n in existing_names) or
            desc in existing_descriptions
        )

        if not has_it:
            gaps.append({
                "name": name,
                "description": expected["description"],
                "priority": "high" if name in ("self_repair", "self_deploy", "income_generation") else "medium",
                "identified_at": now_iso(),
            })

    return gaps


def _create_gap_issues(gaps: list) -> int:
    """Create GitHub issues for capability gaps."""
    if not GITHUB_TOKEN:
        return 0

    created = 0
    for gap in gaps[:3]:  # Max 3 issues per run
        try:
            url = f"https://api.github.com/repos/{OWNER}/evez-agentnet/issues"
            body = f"**Capability Gap Identified**\n\n**Missing:** {gap['name']}\n**Description:** {gap['description']}\n**Priority:** {gap['priority']}\n\n*Auto-identified by capability registry. Requires human review.*"
            payload = json.dumps({
                "title": f"[CAPABILITY GAP] {gap['name']}: {gap['description'][:60]}",
                "body": body,
                "labels": ["capability-gap", "auto-generated"],
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    created += 1
        except Exception as e:
            log.warning(f"Gap issue creation failed: {e}")

    return created


# ── Main entry point ──

def run() -> dict:
    """Scan all capabilities and update the registry."""
    log.info(f"Capability Registry starting — {now_iso()}")

    all_capabilities = []

    # Scan local repo
    local_caps = scan_local_repo(".")
    all_capabilities.extend(local_caps)
    log.info(f"  Local repo: {len(local_caps)} capabilities")

    # Scan skills
    skill_caps = scan_skills()
    all_capabilities.extend(skill_caps)
    log.info(f"  Skills: {len(skill_caps)} capabilities")

    # Scan remote repos
    for repo in REPO_SCAN_CONFIG:
        if repo == "evez-agentnet":
            continue  # Already scanned locally
        remote_caps = scan_remote_repo(repo)
        all_capabilities.extend(remote_caps)
        log.info(f"  {repo}: {len(remote_caps)} capabilities")

    # Deduplicate by name+repo
    seen = set()
    unique = []
    for cap in all_capabilities:
        key = f"{cap['repo']}:{cap['name']}"
        if key not in seen:
            seen.add(key)
            unique.append(cap)

    # Gap analysis
    gaps = _identify_gaps(unique)
    log.info(f"  Capability gaps: {len(gaps)}")

    # Create issues for gaps (gated by GITHUB_TOKEN)
    issues_created = _create_gap_issues(gaps)

    registry = {
        "capabilities": unique,
        "gaps": gaps,
        "stats": {
            "total_capabilities": len(unique),
            "by_type": {},
            "by_repo": {},
            "gaps_found": len(gaps),
            "issues_created": issues_created,
        },
        "updated_at": now_iso(),
    }

    for cap in unique:
        t = cap["type"]
        r = cap["repo"]
        registry["stats"]["by_type"][t] = registry["stats"]["by_type"].get(t, 0) + 1
        registry["stats"]["by_repo"][r] = registry["stats"]["by_repo"].get(r, 0) + 1

    _save_capabilities(registry)
    log.info(f"  TOTAL: {len(unique)} capabilities registered")
    return registry["stats"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = run()
    print(json.dumps(stats, indent=2))
