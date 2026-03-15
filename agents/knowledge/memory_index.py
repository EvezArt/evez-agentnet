#!/usr/bin/env python3
"""
Memory Indexer — indexes everything the system has ever learned.
Reads git history, decisions, knowledge discoveries.
Builds a searchable index with semantic search and knowledge decay tracking.
"""
import os
import json
import logging
import hashlib
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("agentnet.knowledge.memory_index")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "EvezArt"

INDEX_PATH = Path("knowledge/index.json")
DISCOVERIES_DIR = Path("knowledge/discoveries")

# Knowledge decay: entries older than this many days get decay penalties
DECAY_THRESHOLD_DAYS = 90
DECAY_RATE = 0.01  # per day beyond threshold


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return {"entries": [], "stats": {}, "updated_at": now_iso()}


def _save_index(index: dict):
    index["updated_at"] = now_iso()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2))


def _entry_id(source: str, key: str) -> str:
    return hashlib.md5(f"{source}:{key}".encode()).hexdigest()[:12]


# ── Git history indexer ──

def index_git_history(repo_path: str = ".") -> list:
    """Index git commit history from the current repo."""
    entries = []
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s", "-100"],
            capture_output=True, text=True, cwd=repo_path, timeout=30,
        )
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) < 3:
                continue
            sha, date, message = parts
            entries.append({
                "id": _entry_id("git", sha[:8]),
                "source": "git_history",
                "type": "commit",
                "title": message.strip(),
                "content": message.strip(),
                "timestamp": date.strip(),
                "keywords": _extract_keywords(message),
                "ref": sha[:8],
            })
    except Exception as e:
        log.warning(f"Git history indexing failed: {e}")
    return entries


def _extract_keywords(text: str) -> list:
    """Extract meaningful keywords from text for search."""
    stop_words = {"the", "a", "an", "is", "was", "are", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "can", "shall",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "and", "but", "or", "not", "no",
                  "this", "that", "it", "its", "all", "each", "any", "some"}
    words = text.lower().split()
    return list(set(w.strip("()[]{}:.,!?\"'") for w in words
                    if len(w) > 2 and w.lower() not in stop_words))[:15]


# ── Decisions indexer ──

def index_decisions() -> list:
    """Index DECISIONS/ entries from evez-autonomous-ledger (if cloned locally)."""
    entries = []
    decisions_dirs = [
        Path("../evez-autonomous-ledger/DECISIONS"),
        Path("DECISIONS"),
    ]
    for decisions_dir in decisions_dirs:
        if not decisions_dir.exists():
            continue
        for fpath in sorted(decisions_dir.glob("*.md")):
            try:
                content = fpath.read_text()[:1000]
                entries.append({
                    "id": _entry_id("decision", fpath.stem),
                    "source": "autonomous_ledger",
                    "type": "decision",
                    "title": fpath.stem.replace("_", " ").replace("-", " "),
                    "content": content[:500],
                    "timestamp": datetime.fromtimestamp(fpath.stat().st_mtime).isoformat(),
                    "keywords": _extract_keywords(content),
                    "ref": str(fpath),
                })
            except Exception as e:
                log.warning(f"Decision indexing failed for {fpath}: {e}")
    return entries


# ── Knowledge discoveries indexer ──

def index_discoveries() -> list:
    """Index all knowledge discoveries."""
    entries = []
    if not DISCOVERIES_DIR.exists():
        return entries
    for fpath in sorted(DISCOVERIES_DIR.glob("*.json")):
        try:
            d = json.loads(fpath.read_text())
            entries.append({
                "id": _entry_id("discovery", d.get("id", fpath.stem)),
                "source": "knowledge_discovery",
                "type": d.get("source", "unknown"),
                "title": d.get("title", ""),
                "content": d.get("summary", ""),
                "timestamp": d.get("discovered_at", now_iso()),
                "keywords": _extract_keywords(f"{d.get('title', '')} {d.get('summary', '')}"),
                "relevance_score": d.get("relevance_score", 0),
                "ref": str(fpath),
            })
        except Exception as e:
            log.warning(f"Discovery indexing failed for {fpath}: {e}")
    return entries


# ── Knowledge decay tracker ──

def _apply_decay(entries: list) -> list:
    """Apply decay scores to old knowledge entries."""
    now = datetime.now(timezone.utc)
    for entry in entries:
        try:
            ts = entry.get("timestamp", "")
            if "T" in ts:
                entry_date = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                entry_date = datetime.fromisoformat(ts)
            if entry_date.tzinfo is None:
                entry_date = entry_date.replace(tzinfo=timezone.utc)
            age_days = (now - entry_date).days
            if age_days > DECAY_THRESHOLD_DAYS:
                decay = (age_days - DECAY_THRESHOLD_DAYS) * DECAY_RATE
                entry["decay_score"] = round(min(1.0, decay), 3)
                entry["stale"] = decay >= 0.5
            else:
                entry["decay_score"] = 0.0
                entry["stale"] = False
        except Exception:
            entry["decay_score"] = 0.0
            entry["stale"] = False
    return entries


# ── Search ──

def search(query: str, index: dict = None, max_results: int = 20) -> list:
    """Search the index by keyword matching."""
    if index is None:
        index = _load_index()

    query_keywords = set(_extract_keywords(query))
    if not query_keywords:
        return []

    scored = []
    for entry in index.get("entries", []):
        entry_keywords = set(entry.get("keywords", []))
        overlap = query_keywords & entry_keywords
        if overlap:
            score = len(overlap) / len(query_keywords)
            # Boost by relevance, penalize by decay
            score += entry.get("relevance_score", 0) * 0.3
            score -= entry.get("decay_score", 0) * 0.5
            scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    return [entry for _, entry in scored[:max_results]]


# ── Main entry point ──

def run() -> dict:
    """Build/update the full memory index."""
    log.info(f"Memory Indexer starting — {now_iso()}")

    all_entries = []

    # Index git history
    git_entries = index_git_history()
    all_entries.extend(git_entries)
    log.info(f"  Git history: {len(git_entries)} entries")

    # Index decisions
    decision_entries = index_decisions()
    all_entries.extend(decision_entries)
    log.info(f"  Decisions: {len(decision_entries)} entries")

    # Index discoveries
    discovery_entries = index_discoveries()
    all_entries.extend(discovery_entries)
    log.info(f"  Discoveries: {len(discovery_entries)} entries")

    # Apply decay
    all_entries = _apply_decay(all_entries)

    # Deduplicate by ID
    seen = set()
    unique = []
    for entry in all_entries:
        if entry["id"] not in seen:
            seen.add(entry["id"])
            unique.append(entry)

    stale_count = sum(1 for e in unique if e.get("stale", False))

    index = {
        "entries": unique,
        "stats": {
            "total_entries": len(unique),
            "by_source": {},
            "stale_entries": stale_count,
            "indexed_at": now_iso(),
        },
        "updated_at": now_iso(),
    }

    # Count by source
    for entry in unique:
        src = entry.get("source", "unknown")
        index["stats"]["by_source"][src] = index["stats"]["by_source"].get(src, 0) + 1

    _save_index(index)
    log.info(f"  TOTAL: {len(unique)} entries indexed ({stale_count} stale)")
    return index["stats"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        query = " ".join(sys.argv[2:])
        results = search(query)
        for r in results:
            print(f"  [{r['source']}] {r['title'][:70]}")
        print(f"\n{len(results)} results")
    else:
        stats = run()
        print(json.dumps(stats, indent=2))
