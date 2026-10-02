#!/usr/bin/env python3
"""
EVEZ MoE — mixture-of-experts router over REAL local models.

There are six Ollama models installed on this host. This routes a task to the
smallest one likely to handle it well, which is the actual point of a MoE: you
pay for the big expert only when the small one is not good enough.

Two-tier gate:

  1. DETERMINISTIC pre-router. Task shape (code / classify / summarise /
     embed / reason) plus a measured quality floor per expert. Zero latency,
     zero cost, always available. This is what runs by default.

  2. JEV GATE (optional). When TYPESAFE_API_KEY is set, Jev evaluates which
     expert suits the task and returns a calibrated distribution with
     confidence. The router uses it only when it clears JEV_MIN_CONFIDENCE,
     and abstains to the deterministic tier otherwise.

Honesty constraints, consistent with the rest of this repo:
  - An expert is only marked available if Ollama actually lists it. No
    aspirational roster.
  - If no expert is available the router says so. It does not silently
    return the biggest model as if routing had succeeded.
  - Routing decisions are logged with the reason, so a bad route is visible.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("evez.moe")

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
ROUTER_LOG = Path("moe/routing.jsonl")

# Task shapes this router understands. Each maps to a preference order —
# cheapest adequate expert first.
TASK_KINDS = ("code", "classify", "summarise", "embed", "reason", "extract")

# Preference order per task kind. Verified against what is installed.
# Cost is the reason for the ordering: a 0.6B model that suffices costs
# roughly a fifth of a 3.2B model in tokens and far less wall-clock.
PREFERENCES: dict[str, list[str]] = {
    "classify":  ["qwen3:0.6b", "hermes3:3b-fast", "hermes3:3b"],
    "extract":   ["qwen3:0.6b", "hermes3:3b-fast"],
    "summarise": ["qwen3:1.7b", "hermes3:3b-fast", "hermes3:3b"],
    "classify_note": [],
    "reason":    ["deepseek-r1:1.5b", "qwen3:1.7b", "hermes3:3b"],
    "code":      ["qwen3:1.7b", "hermes3:3b", "deepseek-r1:1.5b"],
    # nomic-embed-text produces VECTORS, not text. It cannot answer a
    # generative prompt, so it must never be picked by the generative router.
    # Embedding is a separate code path (call /api/embeddings directly).
    "embed":     [],          # generative routing: no embed model qualifies
}

# Cheap keyword cues for the deterministic tier. Deliberately shallow: this
# tier exists so routing still works with no API key, not to be clever.
CUES = {
    "code": ("def ", "class ", "import ", "function", "```", "refactor",
             "traceback", "exception", "->", "async "),
    # Added after test_moe_router caught classification falling through to
    # summarise: there were no classify cues at all, so the cheapest-model
    # path was never exercised.
    "classify": ("classify", "categorize", "categorise", "label",
                 "is this", "does this", "which category", "route this",
                 "triage", "intent", "classify:"),
    "reason": ("why", "because", "prove", "derive", "trade-off", "tradeoff",
               "consequence", "if ", "implies", "therefore"),
    "summarise": ("summar", "tldr", "brief", "condense", "shorten"),
    "extract": ("extract", "parse", "json", "field", "regex", "pull out"),
    "embed": ("embed", "embedding", "vector", "similarity", "semantic"),
}


@dataclass
class Expert:
    name: str
    size_bytes: int = 0
    params: str = "?"
    context: int | None = None


@dataclass
class Route:
    expert: str | None
    task_kind: str
    gate: str                      # "deterministic" | "jev" | "none"
    reason: str
    confidence: float | None = None
    candidates: list[str] = field(default_factory=list)
    probabilities: dict = field(default_factory=dict)


# ── roster ─────────────────────────────────────────────────────────────────
def installed_experts(timeout: int = 8) -> dict[str, Expert]:
    """Experts Ollama ACTUALLY reports. Verified, never assumed."""
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=timeout) as r:
            d = json.loads(r.read())
    except Exception as e:
        log.warning("Ollama unreachable: %s", str(e)[:100])
        return {}

    out: dict[str, Expert] = {}
    for m in d.get("models", []):
        det = m.get("details", {}) or {}
        name = m.get("name", "")
        if not name:
            continue
        out[name] = Expert(
            name=name,
            size_bytes=m.get("size", 0),
            params=str(det.get("parameter_size", "?")),
            context=m.get("context_length") or det.get("context_length"),
        )
    return out


# ── tier 1: deterministic ──────────────────────────────────────────────────
def classify_kind(text: str) -> tuple[str, float]:
    """Return (kind, cue_strength). Shallow by design."""
    low = (text or "")[:4000].lower()
    best, best_hits = "reason", 0
    for kind, cues in CUES.items():
        hits = sum(1 for c in cues if c in low)
        if hits > best_hits:
            best, best_hits = kind, hits
    # no cue at all -> default to summarise, the safest cheap generalist
    if best_hits == 0:
        return "summarise", 0.0
    return best, min(1.0, best_hits / 3.0)


def deterministic_route(text: str, experts: dict[str, Expert]) -> Route:
    kind, strength = classify_kind(text)
    prefs = [p for p in PREFERENCES.get(kind, []) if p in experts]

    # An embed-only model can never answer a generative prompt, regardless of
    # what the preference list says.
    generative = [p for p in prefs if "embed" not in p]
    if generative:
        prefs = generative

    if not prefs:
        # fall back to the smallest installed model that can generate text
        talkers = [e for e in experts.values() if "embed" not in e.name]
        if not talkers:
            return Route(None, kind, "none", "no non-embedding expert installed")
        smallest = min(talkers, key=lambda e: e.size_bytes)
        return Route(smallest.name, kind, "deterministic",
                     f"no preference for {kind!r}; smallest talker "
                     f"({smallest.params})", strength, prefs)

    chosen = prefs[0]
    reason = f"{kind} -> {chosen} ({experts[chosen].params})"
    if len(prefs) > 1:
        reason += f"; escalate to {prefs[1]} on poor output"
    return Route(chosen, kind, "deterministic", reason, strength, prefs)


# ── tier 2: Jev gate ───────────────────────────────────────────────────────
def jev_route(text: str, experts: dict[str, Expert]) -> Route:
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        return Route(None, "", "none", "no TYPESAFE_API_KEY")

    options = [e.name for e in experts.values() if "embed" not in e.name]
    if not options:
        return Route(None, "", "none", "no candidates")

    from jev_client import JevUnavailable, evaluate
    try:
        ans = evaluate(
            {"task": (text or "")[:4000], "available_experts": options},
            {"expert": {
                "type": "choice",
                "instructions": "Which available model handles this task best, "
                               "balancing capability against cost?",
                "criteria": {name: f"model {name}" for name in options},
            }},
        )
    except JevUnavailable as e:
        return Route(None, "", "none", f"jev unavailable: {str(e)[:100]}")

    a = ans["expert"]
    conf = a.confidence or 0.0
    min_conf = float(os.environ.get("JEV_MIN_CONFIDENCE", "0.55"))
    if conf < min_conf:
        return Route(None, "", "jev",
                     f"abstained: confidence {conf:.2f} < {min_conf:.2f}",
                     conf, [], a.probabilities)
    return Route(a.choice, "", "jev", f"jev chose {a.choice} (conf {conf:.2f})",
                 conf, options, a.probabilities)


# ── public API ─────────────────────────────────────────────────────────────
def route(text: str, prefer: str | None = None) -> Route:
    """Pick an expert. `prefer` forces a task kind over inference."""
    experts = installed_experts()
    if not experts:
        return Route(None, prefer or "", "none", "Ollama unreachable or empty")

    if prefer and prefer in PREFERENCES:
        prefs = [p for p in PREFERENCES[prefer] if p in experts]
        if prefs:
            return Route(prefs[0], prefer, "forced",
                         f"forced kind={prefer}", 1.0, prefs)

    j = jev_route(text, experts)
    if j.expert:
        j.task_kind = classify_kind(text)[0]
        _log_route(j, text)
        return j

    d = deterministic_route(text, experts)
    if j.gate == "jev" and j.reason.startswith("abstained"):
        d.reason = f"{d.reason} (jev abstained: {j.reason})"
    _log_route(d, text)
    return d


def _log_route(r: Route, text: str) -> None:
    ROUTER_LOG.parent.mkdir(exist_ok=True)
    with open(ROUTER_LOG, "a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "expert": r.expert, "task_kind": r.task_kind, "gate": r.gate,
            "reason": r.reason, "confidence": r.confidence,
            "probabilities": r.probabilities,
            "prompt_chars": len(text or ""),
            "preview": (text or "")[:80],
        }) + "\n")


def status() -> dict:
    experts = installed_experts()
    return {
        "ollama": OLLAMA,
        "reachable": bool(experts),
        "experts": {n: {"params": e.params,
                         "mb": round(e.size_bytes / 1048576),
                         "context": e.context}
                    for n, e in sorted(experts.items())},
        "task_kinds": [k for k in TASK_KINDS if PREFERENCES.get(k)],
        "jev_gate": bool(os.environ.get("TYPESAFE_API_KEY", "").strip()),
        "routes_logged": (sum(1 for _ in open(ROUTER_LOG))
                          if ROUTER_LOG.exists() else 0),
    }
