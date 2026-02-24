#!/usr/bin/env python3
"""
evez-agentnet/browser_agent/tasks/groq_login.py

Retrieves GROQ_API_KEY from console.groq.com.
Pattern:
  1. Trigger magic-link email
  2. otp_relay fetches link from Gmail within 25s
  3. Browser navigates to link BEFORE returning (instant, no wait)
  4. Creates new key, returns gsk_ string
  5. Auto-injects into GitHub Actions secrets
"""
import os
import logging
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from browser_agent.otp_relay import watch_inbox
from browser_agent.agent import BrowserAgent
from browser_agent.credential_vault import set_github_secret

log = logging.getLogger("agentnet.browser_agent.groq_login")

PROFILE_ID = "groq-evez"

TRIGGER_TASK = """
1. Navigate to https://console.groq.com/keys
2. Click 'Continue with email'
3. Enter email: rubikspubes69@gmail.com
4. Click Continue
5. You will see 'Check your email'. Output: MAGIC_LINK_TRIGGERED
6. Stop immediately after outputting that text.
"""

USE_LINK_TASK = """
Navigate to this URL immediately without any wait:
{magic_link}

After the redirect lands on console.groq.com:
1. Navigate to https://console.groq.com/keys
2. Click 'Create API key'
3. Name it: evez-agentnet
4. Click Create
5. The key appears ONCE. It starts with gsk_. Copy the FULL key.
6. Return ONLY the gsk_ key string.
"""


def run() -> dict:
    # Step 1: Trigger the magic link email
    trigger_agent = BrowserAgent(profile_id="groq-trigger-tmp")
    trigger_result = trigger_agent.run_task(task=TRIGGER_TASK)

    if "MAGIC_LINK_TRIGGERED" not in trigger_result.get("output", ""):
        return {"success": False, "error": "Failed to trigger magic link"}

    # Step 2: Race the inbox — grab link before Stytch marks it used
    try:
        auth = watch_inbox("groq.com", subject_keyword="login", max_wait=25)
    except TimeoutError:
        return {"success": False, "error": "Magic link email timeout"}

    if auth["type"] != "magic_link":
        return {"success": False, "error": f"Unexpected auth type: {auth['type']}"}

    magic_link = auth["value"]
    log.info(f"Magic link captured: {magic_link[:60]}...")

    # Step 3: Navigate to magic link FIRST, then get key — same agent run
    key_agent = BrowserAgent(profile_id=PROFILE_ID)
    result = key_agent.run_task(
        task=USE_LINK_TASK.format(magic_link=magic_link),
        start_url=magic_link,  # start_url = direct navigation, no wait
        max_attempts=2,
    )

    if result["success"] and "gsk_" in result.get("output", ""):
        # Extract gsk_ key from output
        output = result["output"]
        start = output.find("gsk_")
        key = output[start:start + 200].split()[0].strip()
        set_github_secret("GROQ_API_KEY", key)
        log.info(f"GROQ_API_KEY retrieved and injected: {key[:20]}...")
        return {"success": True, "key": key}

    return {"success": False, "error": result.get("error", result.get("output", "")[:100])}


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(), indent=2))
