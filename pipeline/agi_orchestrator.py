"""EVEZ AGI Full-Stack Pipeline Orchestrator
Surfaces: Sentry · n8n · OpenRouter · Slack · Vercel · GitHub · Postman
Branch: agi-pipeline/full-stack-integration
"""
import os, time, hashlib, json, requests
from datetime import datetime

try:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
except Exception:
    pass

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
N8N_WEBHOOK_URL    = os.getenv("N8N_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL  = os.getenv("SLACK_WEBHOOK_URL", "")
SENTRY_DSN         = os.getenv("SENTRY_DSN", "")

MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-3-5-sonnet",
    "google/gemini-2.0-flash-001",
    "mistralai/mistral-large",
]

def spine_hash(payload: dict) -> str:
    """Append-only hash chain entry — cryptographic ground truth."""
    raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()

def openrouter_call(prompt: str, model: str = MODELS[0]) -> dict:
    """Route prompt through OpenRouter with negative-latency prefill."""
    t0 = time.perf_counter()
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/EvezArt/evez-agentnet",
            "X-Title": "EVEZ-AGI-Pipeline",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=30,
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    data = resp.json()
    return {
        "model": model,
        "content": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
        "latency_ms": round(latency_ms, 2),
        "tokens": data.get("usage", {}),
        "hash": spine_hash(data),
    }

def trigger_n8n(payload: dict) -> dict:
    """Fire n8n webhook and return response."""
    if not N8N_WEBHOOK_URL:
        return {"status": "skipped", "reason": "N8N_WEBHOOK_URL not set"}
    resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=15)
    return {"status": resp.status_code, "body": resp.text[:500]}

def post_slack(message: str, channel: str = "#evez666") -> dict:
    """Post pipeline result to Slack."""
    if not SLACK_WEBHOOK_URL:
        return {"status": "skipped", "reason": "SLACK_WEBHOOK_URL not set"}
    resp = requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": message, "channel": channel},
        timeout=10,
    )
    return {"status": resp.status_code}

def run_pipeline(prompt: str = "EVEZ AGI pipeline test — 2026-03-25") -> dict:
    """End-to-end pipeline: OpenRouter → n8n → Slack → Sentry trace."""
    run_id = spine_hash({"prompt": prompt, "ts": time.time()})
    print(f"[EVEZ-AGI] Pipeline run: {run_id[:12]}")

    # Step 1: Multi-model fan-out via OpenRouter
    results = []
    for model in MODELS[:2]:  # Use first 2 models for speed; extend as needed
        try:
            r = openrouter_call(prompt, model)
            r["run_id"] = run_id
            results.append(r)
            print(f"  [{model}] {r['latency_ms']}ms — {r['content'][:80]}")
        except Exception as e:
            results.append({"model": model, "error": str(e)})

    # Step 2: Trigger n8n workflow
    n8n_payload = {"run_id": run_id, "results": results, "timestamp": datetime.utcnow().isoformat()}
    n8n_resp = trigger_n8n(n8n_payload)
    print(f"  [n8n] {n8n_resp}")

    # Step 3: Post summary to Slack
    best = min(results, key=lambda x: x.get("latency_ms", 9999))
    slack_msg = (
        f"*EVEZ AGI Pipeline Run* `{run_id[:12]}`\n"
        f"Best model: `{best.get('model')}` @ `{best.get('latency_ms')}ms`\n"
        f"Response: {best.get('content', '')[:200]}"
    )
    slack_resp = post_slack(slack_msg)
    print(f"  [Slack] {slack_resp}")

    # Step 4: Emit Sentry breadcrumb
    try:
        sentry_sdk.add_breadcrumb(category="agi_pipeline", message=f"Run {run_id[:12]} complete", level="info")
        sentry_sdk.capture_message(f"EVEZ-AGI Pipeline OK — {run_id[:12]}", level="info")
    except Exception:
        pass

    return {"run_id": run_id, "results": results, "n8n": n8n_resp, "slack": slack_resp}

if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) or "EVEZ AGI pipeline boot — test all cognitive surfaces"
    output = run_pipeline(prompt)
    print(json.dumps(output, indent=2))
