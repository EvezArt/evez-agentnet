"""
pipeline/agi_orchestrator.py — evez-agentnet
AGI Full-Stack Pipeline — resolves issue #16.

Wires: OpenRouter → n8n → Slack → Sentry → Vercel
Single entry point: python pipeline/agi_orchestrator.py

Surfaces:
  1. OpenRouter multi-model fan-out (Cipher trunk prompt)
  2. n8n webhook trigger (FIRE event routing)
  3. Slack notification (status + breakthroughs)
  4. Sentry error capture (spine error events)
  5. Vercel cron health check (trunk status ping)
"""

import os, json, hashlib, requests, time, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agi_orchestrator")

SPINE_PATH = Path("spine/spine.jsonl")

# ── Config ────────────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GROQ_API_KEY")
N8N_WEBHOOK_URL    = os.environ.get("N8N_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL  = os.environ.get("SLACK_WEBHOOK_URL", "")
SENTRY_DSN         = os.environ.get("SENTRY_DSN", "")
VERCEL_URL         = os.environ.get("VERCEL_URL", "https://evez-agentnet.vercel.app")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")

TRUNK_PROMPT = """You are the EVEZ Trunk — operating inside the EVEZ autonomous cognition system.
Your job: advance the system state.
For any objective: (1) reduce it to a trunk goal, (2) decompose into branches,
(3) assign each branch a role, (4) return each branch result to trunk,
(5) compress best logic into canonical state, (6) emit minimal decisions for human.
Default: automation, evidence, reintegration. No explanations unless asked."""

MODELS = [
    "anthropic/claude-3-haiku",
    "openai/gpt-4o-mini",
    "meta-llama/llama-3-8b-instruct:free",
]

# ── Spine ─────────────────────────────────────────────────────────────────────

def append_spine(event_type: str, data: dict) -> dict:
    SPINE_PATH.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "type": event_type, "data": data}
    raw = json.dumps(entry, sort_keys=True)
    entry["sha256"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
    with open(SPINE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

# ── Surface 1: OpenRouter multi-model fan-out ─────────────────────────────────

def openrouter_complete(prompt: str, model: str, system: str = TRUNK_PROMPT) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        log.warning("No OPENROUTER_API_KEY or GROQ_API_KEY set")
        return None
    try:
        # Try OpenRouter first, fallback to Groq
        if OPENROUTER_API_KEY.startswith("gsk_"):
            # Groq
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ], "max_tokens": 500},
                timeout=30
            )
        else:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://github.com/EvezArt/evez-agentnet"},
                json={"model": model, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ], "max_tokens": 500},
                timeout=30
            )
        if r.ok:
            return r.json()["choices"][0]["message"]["content"].strip()
        log.warning(f"LLM {model} returned {r.status_code}: {r.text[:100]}")
        return None
    except Exception as e:
        log.error(f"LLM error ({model}): {e}")
        return None

def fan_out(prompt: str, models: List[str] = MODELS) -> Dict[str, Optional[str]]:
    """Fan out to multiple models, return all responses."""
    results = {}
    for m in models:
        log.info(f"  → querying {m}")
        results[m] = openrouter_complete(prompt, m)
        time.sleep(0.5)
    return results

# ── Surface 2: n8n webhook ────────────────────────────────────────────────────

def trigger_n8n(event_type: str, payload: dict) -> bool:
    if not N8N_WEBHOOK_URL:
        log.info("n8n webhook not configured — skipping")
        return False
    try:
        r = requests.post(N8N_WEBHOOK_URL, json={
            "event_type": event_type,
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "agi_orchestrator",
        }, timeout=10)
        log.info(f"n8n trigger: {r.status_code}")
        return r.ok
    except Exception as e:
        log.error(f"n8n error: {e}")
        return False

# ── Surface 3: Slack notification ─────────────────────────────────────────────

def slack_notify(text: str, blocks: Optional[list] = None) -> bool:
    if not SLACK_WEBHOOK_URL:
        log.info("Slack webhook not configured — skipping")
        return False
    try:
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        r = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return r.ok
    except Exception as e:
        log.error(f"Slack error: {e}")
        return False

# ── Surface 4: Sentry ─────────────────────────────────────────────────────────

def sentry_capture(error: str, context: dict = None) -> bool:
    if not SENTRY_DSN:
        log.info("Sentry DSN not configured — skipping")
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(SENTRY_DSN)
        with sentry_sdk.push_scope() as scope:
            for k, v in (context or {}).items():
                scope.set_extra(k, v)
            sentry_sdk.capture_message(error, "error")
        return True
    except Exception as e:
        log.warning(f"Sentry error: {e}")
        return False

# ── Surface 5: Vercel health check ────────────────────────────────────────────

def check_vercel_health() -> dict:
    try:
        r = requests.get(f"{VERCEL_URL}/health", timeout=10)
        if r.ok:
            return {"ok": True, "data": r.json()}
        return {"ok": False, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── Main Pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(objective: str = None) -> dict:
    if not objective:
        objective = "Audit current EVEZ system state. Identify top 3 actions to advance the trunk. Return branch contracts."

    log.info("=" * 60)
    log.info("AGI FULL-STACK PIPELINE — CIPHER TRUNK")
    log.info("=" * 60)

    results = {}
    ts_start = datetime.now(timezone.utc).isoformat()

    # Step 1: Multi-model fan-out
    log.info(f"\n[1] OpenRouter fan-out — objective: {objective[:60]}...")
    llm_results = fan_out(objective)
    valid = {m: r for m, r in llm_results.items() if r}
    log.info(f"    {len(valid)}/{len(MODELS)} models responded")
    results["llm_responses"] = llm_results

    # Step 2: Compress to trunk state
    best_response = next((r for r in valid.values() if r), "No LLM response available")
    spine_entry = append_spine("agi_pipeline_run", {
        "objective": objective[:200],
        "models_queried": list(llm_results.keys()),
        "models_responded": list(valid.keys()),
        "best_response_len": len(best_response),
    })
    log.info(f"    spine: {spine_entry['sha256']}")
    results["spine_entry"] = spine_entry

    # Step 3: n8n trigger
    log.info("\n[2] n8n trigger...")
    n8n_ok = trigger_n8n("pipeline_complete", {
        "objective": objective[:200],
        "spine_hash": spine_entry["sha256"],
        "models_responded": list(valid.keys()),
    })
    results["n8n"] = {"triggered": n8n_ok}

    # Step 4: Slack
    log.info("\n[3] Slack notification...")
    phi = 0.0
    if SPINE_PATH.exists():
        n = sum(1 for _ in open(SPINE_PATH))
        phi = round(min(0.995, 0.5 + (n / (n + 100)) * 0.495), 4)
    slack_ok = slack_notify(
        f"🔥 EVEZ Pipeline complete | φ={phi} | {len(valid)}/{len(MODELS)} models | hash={spine_entry['sha256']}\n> {best_response[:200]}"
    )
    results["slack"] = {"sent": slack_ok}

    # Step 5: Vercel health
    log.info("\n[4] Vercel health check...")
    vercel = check_vercel_health()
    results["vercel"] = vercel
    log.info(f"    vercel: {'✓' if vercel['ok'] else '✗'}")

    results["ts_start"] = ts_start
    results["ts_end"] = datetime.now(timezone.utc).isoformat()
    results["phi"] = phi

    log.info("\n" + "=" * 60)
    log.info(f"PIPELINE COMPLETE | φ={phi} | hash={spine_entry['sha256']}")
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    import sys
    objective = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    result = run_pipeline(objective)
    print(json.dumps({
        "phi": result.get("phi"),
        "spine": result.get("spine_entry", {}).get("sha256"),
        "llm_count": len([r for r in result.get("llm_responses", {}).values() if r]),
        "n8n": result.get("n8n", {}).get("triggered"),
        "slack": result.get("slack", {}).get("sent"),
        "vercel": result.get("vercel", {}).get("ok"),
    }, indent=2))
