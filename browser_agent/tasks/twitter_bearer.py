#!/usr/bin/env python3
"""
evez-agentnet/browser_agent/tasks/twitter_bearer.py

Retrieves Twitter Bearer Token from developer.twitter.com.
Uses persistent Hyperbrowser profile so X login survives across runs.
Self-heals: if bearer is rotated or session expired, re-auths and re-fetches.
"""
import os
import logging
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from browser_agent.agent import BrowserAgent
from browser_agent.credential_vault import set_github_secret

log = logging.getLogger("agentnet.browser_agent.twitter_bearer")

# Persistent profile ID — auth is saved on first successful login
PROFILE_ID = "twitter-evez666"

LOGIN_TASK = """
You need to log into X (Twitter) as user EVEZ666 and then access the developer portal.

STEP 1 — X Login:
1. Navigate to https://x.com/i/flow/login
2. In the username/email field enter: EVEZ666
3. Click Next
4. If asked to confirm identity, enter: rubikspubes69@gmail.com and click Next
5. Enter password: Evezpassword666
6. Click Log in
7. If you see a verification code prompt, output exactly: NEEDS_EMAIL_CODE and stop.
8. Once logged in successfully, continue to Step 2.

STEP 2 — Developer Portal:
9. Navigate to https://developer.twitter.com/en/portal/dashboard
10. Find the app (look for EVEZ666 or any project listed)
11. Click on the app/project name
12. Click 'Keys and tokens'
13. In the Bearer Token section: if the value shows asterisks or is hidden, click 'Regenerate'. Confirm.
14. Copy the complete Bearer Token (starts with AAAA)
15. Return ONLY the Bearer Token string — nothing else.
"""


def run() -> dict:
    agent = BrowserAgent(
        profile_id=PROFILE_ID,
        otp_sender_domain="twitter.com",
    )
    result = agent.run_task(
        task=LOGIN_TASK,
        max_attempts=3,
    )

    if result["success"] and result["output"].startswith("AAAA"):
        bearer = result["output"].strip()
        log.info(f"Bearer Token retrieved: {bearer[:20]}...")
        # Auto-inject into GitHub Actions secrets
        set_github_secret("TWITTER_BEARER_TOKEN", bearer)
        return {"success": True, "token": bearer}

    log.error(f"Failed: {result.get('error', result.get('output', '')[:100])}")
    return {"success": False, "error": result.get("error", "unknown")}


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(), indent=2))
