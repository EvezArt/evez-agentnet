#!/usr/bin/env python3
"""
Knowledge Harvester — continuously gathers knowledge from public sources.
Scans arXiv, GitHub trending, HuggingFace model cards, and AI news.
Stores discoveries as structured JSON in knowledge/discoveries/.
"""
import os
import json
import logging
import hashlib
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("agentnet.knowledge.harvester")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DISCOVERIES_DIR = Path("knowledge/discoveries")
DISCOVERIES_DIR.mkdir(parents=True, exist_ok=True)

RELEVANCE_KEYWORDS = [
    "autonomous agent", "multi-agent", "self-improving", "meta-learning",
    "reinforcement learning", "llm agent", "tool use", "code generation",
    "quantum computing", "self-repair", "knowledge graph", "reasoning",
    "chain of thought", "agentic", "swarm intelligence", "orchestration",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def discovery_id():
    return f"discovery_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"


def _score_relevance(text: str) -> float:
    """Score relevance 0.0-1.0 based on keyword density."""
    text_lower = text.lower()
    hits = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text_lower)
    return min(1.0, hits / 3.0)


def _save_discovery(discovery: dict) -> str:
    """Save a discovery to knowledge/discoveries/ as JSON."""
    fpath = DISCOVERIES_DIR / f"{discovery['id']}.json"
    fpath.write_text(json.dumps(discovery, indent=2))
    return str(fpath)


def _gh_headers() -> dict:
    headers = {"User-Agent": "evez-agentnet/1.0", "Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


# ── arXiv scanner ──

def scan_arxiv() -> list:
    """Scan arXiv for latest AI agent, autonomous systems, and quantum research."""
    discoveries = []
    queries = [
        "autonomous+agent+LLM",
        "multi-agent+reinforcement+learning",
        "quantum+computing+optimization",
    ]
    for query in queries:
        try:
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
            req = urllib.request.Request(url, headers={"User-Agent": "evez-agentnet/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode()

            # Simple XML parsing without external deps
            entries = data.split("<entry>")[1:]
            for entry in entries:
                title = _extract_xml(entry, "title").strip().replace("\n", " ")
                summary = _extract_xml(entry, "summary").strip().replace("\n", " ")[:500]
                link = _extract_xml(entry, "id")

                if not title:
                    continue

                relevance = _score_relevance(f"{title} {summary}")
                if relevance < 0.1:
                    continue

                discoveries.append({
                    "id": discovery_id(),
                    "source": "arxiv",
                    "title": title,
                    "summary": summary,
                    "relevance_score": round(relevance, 2),
                    "applicability": _infer_applicability(title, summary),
                    "url": link,
                    "discovered_at": now_iso(),
                })
        except Exception as e:
            log.warning(f"arXiv scan ({query}): {e}")

    return discoveries


def _extract_xml(text: str, tag: str) -> str:
    """Extract text between XML tags (simple, no deps)."""
    start = text.find(f"<{tag}>")
    if start == -1:
        start = text.find(f"<{tag} ")
        if start == -1:
            return ""
        start = text.find(">", start) + 1
    else:
        start += len(f"<{tag}>")
    end = text.find(f"</{tag}>", start)
    return text[start:end] if end != -1 else ""


def _infer_applicability(title: str, summary: str) -> str:
    """Infer how this could improve EVEZ-OS."""
    text = f"{title} {summary}".lower()
    if "agent" in text and ("tool" in text or "code" in text):
        return "Could enhance agent tool-use or code generation capabilities"
    if "multi-agent" in text or "swarm" in text:
        return "Could improve multi-agent coordination in agentnet orchestrator"
    if "reinforcement" in text or "meta-learn" in text:
        return "Could enhance meta-learner and agent self-improvement loops"
    if "quantum" in text:
        return "Could provide quantum-inspired optimization for resource allocation"
    if "knowledge" in text or "graph" in text:
        return "Could improve knowledge representation and retrieval"
    if "reasoning" in text or "chain" in text:
        return "Could improve agent reasoning and decision quality"
    return "General AI advancement applicable to autonomous agent systems"


# ── GitHub trending scanner ──

def scan_github_trending() -> list:
    """Scan GitHub for trending AI/agent repos with new techniques."""
    discoveries = []
    queries = [
        "agent framework language:python stars:>50 pushed:>2026-02-01",
        "autonomous AI tool-use stars:>20 pushed:>2026-02-01",
        "LLM orchestration stars:>30 pushed:>2026-02-01",
    ]
    for query in queries:
        try:
            url = f"https://api.github.com/search/repositories?q={urllib.request.quote(query)}&sort=updated&order=desc&per_page=5"
            req = urllib.request.Request(url, headers=_gh_headers())
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            for repo in data.get("items", []):
                name = repo.get("full_name", "")
                desc = repo.get("description", "") or ""
                relevance = _score_relevance(f"{name} {desc}")

                discoveries.append({
                    "id": discovery_id(),
                    "source": "github",
                    "title": f"{name}: {desc[:120]}",
                    "summary": f"Stars: {repo.get('stargazers_count', 0)}, Language: {repo.get('language', 'N/A')}, Topics: {', '.join(repo.get('topics', [])[:5])}",
                    "relevance_score": round(max(relevance, 0.3), 2),
                    "applicability": f"New techniques/patterns from {name} applicable to EVEZ-OS agent architecture",
                    "url": repo.get("html_url", ""),
                    "discovered_at": now_iso(),
                })
        except Exception as e:
            log.warning(f"GitHub trending scan: {e}")

    return discoveries


# ── HuggingFace model card scanner ──

def scan_huggingface() -> list:
    """Scan HuggingFace for new models relevant to agent capabilities."""
    discoveries = []
    try:
        url = "https://huggingface.co/api/models?sort=lastModified&direction=-1&limit=10&filter=text-generation"
        req = urllib.request.Request(url, headers={"User-Agent": "evez-agentnet/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            models = json.loads(resp.read())

        for model in models:
            model_id = model.get("modelId", "")
            tags = model.get("tags", [])
            pipeline = model.get("pipeline_tag", "")
            downloads = model.get("downloads", 0)

            relevance = _score_relevance(f"{model_id} {' '.join(tags)}")
            if downloads > 10000:
                relevance = min(1.0, relevance + 0.2)

            discoveries.append({
                "id": discovery_id(),
                "source": "huggingface",
                "title": f"Model: {model_id}",
                "summary": f"Pipeline: {pipeline}, Tags: {', '.join(tags[:5])}, Downloads: {downloads}",
                "relevance_score": round(max(relevance, 0.2), 2),
                "applicability": f"New model capabilities for agent synthesis via {pipeline} pipeline",
                "url": f"https://huggingface.co/{model_id}",
                "discovered_at": now_iso(),
            })
    except Exception as e:
        log.warning(f"HuggingFace scan: {e}")

    return discoveries


# ── AI news scanner ──

def scan_ai_news() -> list:
    """Scan AI news from public GitHub discussions and trending topics."""
    discoveries = []
    try:
        # Use GitHub search for recent AI-related discussions/repos as news proxy
        url = "https://api.github.com/search/repositories?q=AI+agent+created:>2026-03-01&sort=stars&order=desc&per_page=5"
        req = urllib.request.Request(url, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        for repo in data.get("items", []):
            desc = repo.get("description", "") or ""
            relevance = _score_relevance(desc)
            discoveries.append({
                "id": discovery_id(),
                "source": "news",
                "title": f"New AI project: {repo.get('full_name', '')}",
                "summary": desc[:300],
                "relevance_score": round(max(relevance, 0.2), 2),
                "applicability": "New AI development potentially relevant to EVEZ-OS capabilities",
                "url": repo.get("html_url", ""),
                "discovered_at": now_iso(),
            })
    except Exception as e:
        log.warning(f"AI news scan: {e}")

    return discoveries


# ── Main entry point ──

def run() -> list:
    """Execute all scanners and return combined discoveries."""
    log.info(f"Knowledge Harvester starting — {now_iso()}")

    all_discoveries = []
    scanners = [
        ("arXiv", scan_arxiv),
        ("GitHub Trending", scan_github_trending),
        ("HuggingFace", scan_huggingface),
        ("AI News", scan_ai_news),
    ]

    for name, scanner_fn in scanners:
        try:
            results = scanner_fn()
            all_discoveries.extend(results)
            log.info(f"  {name}: {len(results)} discoveries")
        except Exception as e:
            log.warning(f"  {name} scanner failed: {e}")

    # Deduplicate by title similarity
    seen_titles = set()
    unique = []
    for d in all_discoveries:
        key = d["title"][:60].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(d)

    # Save all discoveries
    for d in unique:
        _save_discovery(d)

    log.info(f"  TOTAL: {len(unique)} unique discoveries saved")
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    discoveries = run()
    for d in discoveries:
        print(f"  [{d['source']}] {d['relevance_score']:.2f} — {d['title'][:80]}")
    print(f"\nTotal: {len(discoveries)} discoveries")
