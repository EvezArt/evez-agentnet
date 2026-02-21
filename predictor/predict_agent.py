#!/usr/bin/env python3
"""
evez-agentnet/predictor/predict_agent.py
Rank + synthesize scan results using Groq llama-3.3-70b-versatile.
Output: ranked list of opportunities with action plans.
"""

import os
import json
import logging
from pathlib import Path

log = logging.getLogger("agentnet.predictor")

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")


def run(scan_results: list) -> list:
    """Rank scan results and generate action plans."""
    if not scan_results:
        return []

    # Score each signal by opportunity value
    scored = []
    for item in scan_results:
        score = _score_signal(item)
        item["opportunity_score"] = score
        scored.append(item)

    # Sort by score descending
    scored.sort(key=lambda x: x["opportunity_score"], reverse=True)
    top = scored[:5]  # top 5 opportunities per round

    # Generate action plan for each via Groq (if available)
    plans = []
    for item in top:
        plan = _generate_action_plan(item)
        plans.append(plan)

    # Write predictions
    out = Path("predictor/predictions.jsonl")
    out.parent.mkdir(exist_ok=True)
    with open(out, "a") as f:
        for p in plans:
            f.write(json.dumps(p) + "\n")

    return plans


def _score_signal(item: dict) -> float:
    """Score a signal by opportunity value (0-1)."""
    score = 0.5
    src = item.get("source", "")
    opp = item.get("opportunity", "")

    # High-value sources
    if src == "polymarket":
        vol = item.get("volume_usd", 0)
        score += min(0.3, vol / 1_000_000)
    elif src == "github_trending":
        stars = item.get("stars", 0)
        score += min(0.2, stars / 100_000)

    # High-value opportunity types
    if opp in ("prediction_report", "twitter_thread", "tutorial_or_integration"):
        score += 0.1

    return min(1.0, score)


def _generate_action_plan(item: dict) -> dict:
    """Generate action plan. Uses Groq if available, else template."""
    plan = {**item, "action_plan": None, "deliverable_type": None}

    opp = item.get("opportunity", "")
    title = item.get("title", "")

    if opp == "prediction_report":
        plan["deliverable_type"] = "gumroad_report"
        plan["action_plan"] = f"Generate prediction analysis report on: {title}. Price $9-19. Post to Gumroad."
    elif opp == "twitter_thread":
        plan["deliverable_type"] = "twitter_thread"
        plan["action_plan"] = f"Write 5-tweet thread on: {title}. Include EVEZ-OS angle."
    elif opp == "tutorial_or_integration":
        plan["deliverable_type"] = "github_post"
        plan["action_plan"] = f"Write integration tutorial for: {title}. Post to Twitter + Gumroad."
    elif opp == "resume_cover_letter_gen":
        plan["deliverable_type"] = "gumroad_product"
        plan["action_plan"] = f"Generate AI-optimized resume/cover letter templates. Price $9-29."
    else:
        plan["deliverable_type"] = "twitter_thread"
        plan["action_plan"] = f"Write tweet thread on: {title}."

    # If Groq available, enhance plan
    if GROQ_KEY:
        try:
            plan["action_plan"] = _groq_enhance(plan["action_plan"], item)
        except Exception as e:
            log.debug(f"Groq enhance failed: {e}")

    return plan


def _groq_enhance(base_plan: str, context: dict) -> str:
    """Enhance action plan with Groq llama synthesis."""
    import urllib.request, urllib.error
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are EVEZ-OS, an income-generating AI agent. Be specific and actionable. 1 paragraph max."},
            {"role": "user", "content": f"Enhance this action plan into a specific, executable step:\n{base_plan}\nContext: {json.dumps(context, default=str)[:300]}"}
        ],
        "max_tokens": 150,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"].strip()
