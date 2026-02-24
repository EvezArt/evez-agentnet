#!/usr/bin/env python3
"""
evez-agentnet/browser_agent/otp_relay.py

Sub-25s Gmail OTP/magic-link relay.
Polls Gmail API in a tight loop the moment an auth email is expected.
Returns magic_link URL or raw OTP code.
"""
import os
import re
import time
import base64
import logging
import urllib.request
import urllib.parse
import json
from typing import Optional

log = logging.getLogger("agentnet.browser_agent.otp_relay")

GMAIL_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "gmail_token.json")


def watch_inbox(
    sender_domain: str,
    subject_keyword: str = "",
    max_wait: int = 25,
    poll_interval: float = 2.0,
) -> dict:
    """
    Poll Gmail for a new email from sender_domain containing subject_keyword.
    Returns dict with keys:
        type: 'magic_link' | 'otp' | 'unknown'
        value: str  (URL or 6-digit code)
        raw_body: str
    Raises TimeoutError if not found within max_wait seconds.
    """
    token = _load_token()
    deadline = time.time() + max_wait
    seen_ids: set = set()

    # Seed seen IDs so we only catch NEW emails
    for msg in _list_messages(token, sender_domain, limit=5):
        seen_ids.add(msg["id"])

    log.info(f"Watching inbox for @{sender_domain} (max {max_wait}s)...")

    while time.time() < deadline:
        time.sleep(poll_interval)
        messages = _list_messages(token, sender_domain, limit=5)
        for msg in messages:
            if msg["id"] in seen_ids:
                continue
            seen_ids.add(msg["id"])
            body = _get_body(token, msg["id"])
            result = _extract_auth(body)
            if result:
                log.info(f"Got auth: type={result['type']} from @{sender_domain}")
                return result

    raise TimeoutError(f"No auth email from @{sender_domain} within {max_wait}s")


def _load_token() -> str:
    """Load Gmail access token from file or env."""
    # Try env first (CI)
    token = os.environ.get("GMAIL_ACCESS_TOKEN", "")
    if token:
        return token
    if os.path.exists(GMAIL_TOKEN_FILE):
        with open(GMAIL_TOKEN_FILE) as f:
            data = json.load(f)
        return data.get("access_token", "")
    raise RuntimeError("No Gmail token available. Set GMAIL_ACCESS_TOKEN env var.")


def _list_messages(token: str, sender_domain: str, limit: int = 5) -> list:
    q = urllib.parse.quote(f"from:@{sender_domain} newer_than:2m")
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={q}&maxResults={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        return data.get("messages", [])
    except Exception as e:
        log.debug(f"Gmail list error: {e}")
        return []


def _get_body(token: str, message_id: str) -> str:
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read())
    return _decode_payload(data.get("payload", {}))


def _decode_payload(payload: dict) -> str:
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
    for part in payload.get("parts", []):
        result = _decode_payload(part)
        if result:
            return result
    return ""


def _extract_auth(body: str) -> Optional[dict]:
    # Magic link patterns
    for pattern in [
        r'https://stytch\.com/v1/magic_links/redirect[^"\s<>]+',
        r'https://[^"\s<>]+magic[^"\s<>]+token=[^"\s<>&]+',
    ]:
        m = re.search(pattern, body)
        if m:
            return {"type": "magic_link", "value": m.group(0), "raw_body": body[:500]}

    # 6-digit OTP patterns
    for pattern in [
        r'\b(\d{6})\b',
        r'code[:\s]+([0-9]{6})',
        r'verification code[:\s]+([0-9]{6})',
    ]:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            code = m.group(1) if m.lastindex else m.group(0)
            if code.isdigit() and len(code) == 6:
                return {"type": "otp", "value": code, "raw_body": body[:500]}

    return None
