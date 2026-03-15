#!/usr/bin/env python3
"""
Learning Engine — processes discoveries and applies them.
Classifies each by: can_apply_now, requires_research, future_potential.
For can_apply_now: generates GitHub issues with implementation plans.
For requires_research: creates research notes.
Maintains a knowledge graph mapping concepts -> repos -> capabilities.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.knowledge.learner")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OWNER = "EvezArt"

DISCOVERIES_DIR = Path("knowledge/discoveries")
RESEARCH_DIR = Path("knowledge/research")
GRAPH_PATH = Path("knowledge/graph.json")

RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

# Repos and their domains for matching discoveries
REPO_DOMAINS = {
    "evez-os": ["self-repair", "kernel", "hyperloop", "quantum", "orchestration"],
    "evez-agentnet": ["agent", "scanner", "predictor", "generator", "income", "multi-agent"],
    "evez-autonomous-ledger": ["governance", "decision", "provenance", "audit"],
    "agentvault": ["vault", "credential", "secret", "security", "authentication"],
    "evez-meme-bus": ["meme", "content", "social", "viral", "engagement"],
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_graph() -> dict:
    """Load knowledge graph."""
    if GRAPH_PATH.exists():
        return json.loads(GRAPH_PATH.read_text())
    return {"concepts": {}, "updated_at": now_iso()}


def _save_graph(graph: dict):
    """Persist knowledge graph."""
    graph["updated_at"] = now_iso()
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))


def _classify_discovery(discovery: dict) -> str:
    """Classify a discovery: can_apply_now, requires_research, or future_potential."""
    score = discovery.get("relevance_score", 0)
    source = discovery.get("source", "")
    title = discovery.get("title", "").lower()

    # GitHub repos with high relevance are more immediately applicable
    if source == "github" and score >= 0.5:
        return "can_apply_now"

    # HuggingFace models with agent-related tags
    if source == "huggingface" and score >= 0.6:
        return "can_apply_now"

    # High relevance arXiv papers need research first
    if source == "arxiv" and score >= 0.4:
        return "requires_research"

    # Low relevance items are future potential
    if score < 0.3:
        return "future_potential"

    # Medium relevance defaults to research
    if score < 0.5:
        return "requires_research"

    return "can_apply_now"


def _match_repos(discovery: dict) -> list:
    """Match a discovery to relevant repos based on keywords."""
    text = f"{discovery.get('title', '')} {discovery.get('summary', '')}".lower()
    matched = []
    for repo, keywords in REPO_DOMAINS.items():
        if any(kw in text for kw in keywords):
            matched.append(repo)
    return matched or ["evez-agentnet"]  # default to agentnet


def _call_groq(prompt: str) -> str:
    """Call Groq for AI synthesis (optional, graceful fallback)."""
    if not GROQ_API_KEY:
        return ""
    try:
        body = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning(f"Groq call failed: {e}")
        return ""


def _create_github_issue(repo: str, title: str, body: str) -> bool:
    """Create a GitHub issue in the target repo."""
    if not GITHUB_TOKEN:
        log.info(f"  [DRY RUN] Would create issue in {repo}: {title[:60]}")
        return False
    try:
        url = f"https://api.github.com/repos/{OWNER}/{repo}/issues"
        payload = json.dumps({
            "title": title,
            "body": body,
            "labels": ["knowledge-expansion", "auto-generated"],
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        log.warning(f"Issue creation failed for {repo}: {e}")
        return False


def _create_research_note(discovery: dict):
    """Create a research note for discoveries requiring deeper investigation."""
    note = {
        "discovery_id": discovery["id"],
        "title": discovery["title"],
        "source": discovery["source"],
        "summary": discovery["summary"],
        "relevance_score": discovery["relevance_score"],
        "applicability": discovery["applicability"],
        "url": discovery.get("url", ""),
        "status": "open",
        "created_at": now_iso(),
        "notes": [],
    }
    fpath = RESEARCH_DIR / f"{discovery['id']}_research.json"
    fpath.write_text(json.dumps(note, indent=2))
    return str(fpath)


def _update_knowledge_graph(discovery: dict, classification: str, repos: list, graph: dict):
    """Update the knowledge graph with a new discovery."""
    # Extract key concepts from title
    title_words = discovery["title"].lower().split()
    concepts = [w for w in title_words if len(w) > 4 and w.isalpha()][:5]

    for concept in concepts:
        if concept not in graph["concepts"]:
            graph["concepts"][concept] = {
                "repos": [],
                "capabilities": [],
                "discoveries": [],
                "first_seen": now_iso(),
            }

        entry = graph["concepts"][concept]
        for repo in repos:
            if repo not in entry["repos"]:
                entry["repos"].append(repo)
        if discovery["id"] not in entry["discoveries"]:
            entry["discoveries"].append(discovery["id"])
        entry["last_updated"] = now_iso()
        entry["classification"] = classification


def _load_discoveries() -> list:
    """Load all unprocessed discoveries."""
    discoveries = []
    if not DISCOVERIES_DIR.exists():
        return discoveries
    for fpath in sorted(DISCOVERIES_DIR.glob("*.json")):
        try:
            d = json.loads(fpath.read_text())
            discoveries.append(d)
        except Exception as e:
            log.warning(f"Bad discovery file {fpath}: {e}")
    return discoveries


def run(discoveries: list = None) -> dict:
    """Process discoveries: classify, create issues/research notes, update graph."""
    log.info(f"Learning Engine starting — {now_iso()}")

    if discoveries is None:
        discoveries = _load_discoveries()

    graph = _load_graph()
    stats = {"can_apply_now": 0, "requires_research": 0, "future_potential": 0, "issues_created": 0}

    for discovery in discoveries:
        classification = _classify_discovery(discovery)
        repos = _match_repos(discovery)
        stats[classification] += 1

        _update_knowledge_graph(discovery, classification, repos, graph)

        if classification == "can_apply_now":
            # Generate implementation issue
            prompt = f"""Given this discovery:
Title: {discovery['title']}
Summary: {discovery['summary']}
Applicability: {discovery['applicability']}

Write a concise GitHub issue body (3-5 bullet points) for implementing this in the EVEZ-OS ecosystem.
Focus on: what to build, which module to modify, expected benefit."""

            ai_body = _call_groq(prompt)
            body = ai_body or f"**Discovery:** {discovery['title']}\n\n**Summary:** {discovery['summary']}\n\n**Applicability:** {discovery['applicability']}\n\n**Source:** {discovery.get('url', 'N/A')}\n\n*Auto-generated by knowledge learner. Requires human review.*"

            for repo in repos[:2]:
                title = f"[KNOWLEDGE] {discovery['title'][:80]}"
                full_body = f"{body}\n\n---\n*Discovery ID: {discovery['id']} | Relevance: {discovery['relevance_score']} | Source: {discovery['source']}*"
                if _create_github_issue(repo, title, full_body):
                    stats["issues_created"] += 1

        elif classification == "requires_research":
            _create_research_note(discovery)

        log.info(f"  [{classification}] {discovery['title'][:60]} -> {', '.join(repos)}")

    _save_graph(graph)
    log.info(f"  Stats: {stats}")
    log.info(f"  Knowledge graph: {len(graph['concepts'])} concepts")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = run()
    print(json.dumps(stats, indent=2))
