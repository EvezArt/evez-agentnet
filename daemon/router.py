"""
daemon/router.py — evez-agentnet
OpenRouter API client with free-model fallback chain.
Resolves: evez-agentnet#15

Env:
  OPENROUTER_API_KEY  — OpenRouter API key (required)
  OPENROUTER_MODEL    — override default model (optional)

Free models tried in order:
  1. mistralai/mistral-7b-instruct:free
  2. google/gemma-3-27b-it:free
  3. meta-llama/llama-3.1-8b-instruct:free
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

log = logging.getLogger("daemon.router")

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

FREE_MODELS = [
    os.environ.get("OPENROUTER_MODEL", "") or "mistralai/mistral-7b-instruct:free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
]


def complete(prompt: str, system: str = "You are a helpful AI coding agent.",
             max_tokens: int = 1024) -> Optional[str]:
    """Try each free model in order, return first successful response."""
    if not API_KEY:
        log.warning("[router] OPENROUTER_API_KEY not set.")
        return None
    for model in FREE_MODELS:
        if not model:
            continue
        result = _call(model, system, prompt, max_tokens)
        if result:
            log.info(f"[router] Got response from {model}")
            return result
        log.warning(f"[router] Model {model} failed, trying next...")
    log.error("[router] All models exhausted.")
    return None


def _call(model: str, system: str, prompt: str, max_tokens: int) -> Optional[str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "https://github.com/EvezArt/evez-agentnet",
            "X-Title": "evez-agentnet-daemon",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        log.error(f"[router] HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        log.error(f"[router] Error: {e}")
        return None
