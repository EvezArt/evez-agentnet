#!/usr/bin/env python3
"""
Inference runner for MoE-routed tasks.

Routing is only meaningful if the routed model produces usable output. This
calls Ollama /api/generate with the selected expert and returns the result
plus real timing, so a route can be judged on quality AND cost.

An embed-only model can never be used here — it has no generative interface.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from moe_router import OLLAMA, route


def generate(text: str, *, prefer: str | None = None, timeout: int = 120,
             system: str | None = None) -> dict:
    """Route, then generate. Returns provenance for every answer."""
    r = route(text, prefer=prefer)

    if r.expert is None:
        return {"ok": False, "error": r.reason, "gate": r.gate,
                "task_kind": r.task_kind}

    if "embed" in r.expert:
        return {"ok": False, "error": f"{r.expert} is embed-only and cannot "
                                       f"generate text", "gate": r.gate}

    # qwen3 and deepseek-r1 emit a SEPARATE "thinking" field and spend
    # num_predict tokens on chain-of-thought before producing any answer.
    # With num_predict=400 the model thought until it hit the limit and
    # returned response="" — a silent empty result, not an error.
    #
    # "think": false disables thinking where the model supports it. The
    # num_predict floor also guards against the same failure on models that
    # ignore the flag.
    is_reasoning_family = any(m in r.expert for m in
                               ("qwen3", "deepseek-r1"))
    options = {
        "temperature": 0.2,
        "num_predict": 1200 if is_reasoning_family else 400,
    }
    payload = {
        "model": r.expert,
        "prompt": text,
        "stream": False,
        "options": options,
        "think": False,
    }
    if system:
        payload["system"] = system

    t0 = time.time()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        return {"ok": False, "expert": r.expert, "error": f"HTTP {e.code}: {detail}"}
    except Exception as e:
        return {"ok": False, "expert": r.expert, "error": str(e)[:200]}

    elapsed = time.time() - t0
    text_out = (d.get("response") or "").strip()

    # An empty response is a FAILURE, not a success with empty text. Without
    # this check the caller sees ok=True and an empty string, which is the
    # "reports an outcome it never achieved" pattern again.
    if not text_out:
        return {
            "ok": False,
            "expert": r.expert,
            "gate": r.gate,
            "task_kind": r.task_kind,
            "error": "model returned no text (likely spent budget on 'thinking')",
            "elapsed_s": round(elapsed, 2),
            "eval_count": d.get("eval_count"),
            "done_reason": d.get("done_reason"),
            "thinking_chars": len(d.get("thinking") or ""),
        }

    return {
        "ok": True,
        "expert": r.expert,
        "gate": r.gate,
        "task_kind": r.task_kind,
        "route_reason": r.reason,
        "confidence": r.confidence,
        "text": text_out,
        "elapsed_s": round(elapsed, 2),
        "eval_count": d.get("eval_count"),
        "prompt_eval_count": d.get("prompt_eval_count"),
        "model_reported": d.get("model"),
        "load_duration_s": round((d.get("load_duration") or 0) / 1e9, 2),
    }


def embed(text: str, model: str = "nomic-embed-text:latest") -> dict:
    """Separate path for embeddings — the generative router never reaches here."""
    req = urllib.request.Request(
        f"{OLLAMA}/api/embeddings",
        data=json.dumps({"model": model, "prompt": text}).encode(),
        method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read())
        return {"ok": True, "model": model, "dim": len(d.get("embedding", [])),
                "embedding": d.get("embedding")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
