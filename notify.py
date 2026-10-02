#!/usr/bin/env python3
"""Send the standing brief to Telegram via the Bot API.

Deliberately does NOT use Hermes gateway delivery or an OpenClaw agent, and
does NOT run a getUpdates polling loop.

Reason: the Telegram bot token in /root/.openclaw/openclaw.json belongs to
OpenClaw, which already long-polls getUpdates for that bot. A second poller
on the same token gets HTTP 409 Conflict and both break. Using the send API
directly — same token, no polling — adds no conflict surface, and mirrors how
evez_delivery/ship.sh already works on this box.

Exit codes: 0 ok | 1 permanent error | 2 transient (safe to retry)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path("/root/evez-agentnet")
BRIEF = REPO / "status/BRIEF.md"
CFG_CANDIDATES = [
    Path("/root/.openclaw/openclaw.json"),
    Path("/workspace/.openclaw/openclaw.json"),
]
TOKEN_RE = re.compile(r"\d{8,}:[A-Za-z0-9_-]{30,}")
API = "https://api.telegram.org/bot{token}/{method}"

# Only alert on these. A brief every 6h is noise if nothing changed.
ALERT_SEVERITIES = {"high"}
STATE_FILE = REPO / "status/.last_alert"


def get_token() -> str:
    env = os.environ.get("TELEGRAM_BOT_TOKEN")
    if env:
        return env.strip()
    for c in CFG_CANDIDATES:
        if c.exists():
            m = TOKEN_RE.search(c.read_text(errors="replace"))
            if m:
                return m.group(0)
    return ""


def get_chat_id() -> str:
    env = os.environ.get("TELEGRAM_CHAT_ID")
    if env:
        return env.strip()
    # ship.sh already hardcodes the recipient; reuse the same value
    sh = Path("/root/.openclaw/workspace/evez_delivery/ship.sh")
    if sh.exists():
        m = re.search(r'CHAT="(\d+)"', sh.read_text(errors="replace"))
        if m:
            return m.group(1)
    return ""


def api(method: str, payload: dict, timeout=25) -> tuple[bool, str]:
    token = get_token()
    if not token:
        return False, "no bot token found"
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        API.format(token=token, method=method), data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read())
            return bool(body.get("ok")), json.dumps(body)[:200]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:200]
        # 409 means a second poller owns this token — surface it clearly
        if e.code == 409:
            return False, "409 Conflict: another getUpdates poller owns this token"
        if e.code == 401:
            return False, f"401 Unauthorized: bad token ({detail})"
        return False, f"HTTP {e.code}: {detail}"
    except Exception as e:
        return False, f"transient: {str(e)[:120]}"


def parse_alerts() -> list[str]:
    if not BRIEF.exists():
        return []
    lines = BRIEF.read_text().splitlines()
    alerts, grab = [], False
    for l in lines:
        if l.startswith("### "):
            grab = "[HIGH]" in l
            if grab:
                alerts.append(l[4:].strip())
        elif grab and l.startswith("- **Action:**"):
            alerts.append("    " + l.replace("- **Action:**", "").strip().strip("`"))
    return alerts


def main() -> int:
    alerts = parse_alerts()
    if not alerts:
        print("no HIGH alerts to send")
        return 0

    high = [a for a in alerts if not a.startswith("    ")]
    actions = [a.strip() for a in alerts if a.startswith("    ")]
    fingerprint = "|".join(high)

    if STATE_FILE.exists() and STATE_FILE.read_text().strip() == fingerprint:
        print("alerts unchanged since last send — suppressing")
        return 0

    chat = get_chat_id()
    if not chat:
        print("no chat id; set TELEGRAM_CHAT_ID")
        return 1

    # Telegram legacy Markdown treats _ * ` [ ] ( ) as markup. Actions carry
    # shell syntax full of parens and underscores, which produced
    # "can't parse entities" on the first live send. Keep the text intact and
    # escape it instead of stripping detail.
    def esc(s: str) -> str:
        out = []
        for ch in s:
            if ch in "_*`[]()~>#+-=|{}.!":
                out.append("\\" + ch)
            else:
                out.append(ch)
        return "".join(out)

    lines = ["*EVEZ \u2014 items needing you*"]
    for i, h in enumerate(high, 1):
        lines.append(f"{i}. *{esc(h.replace('[HIGH] ', ''))}*")
    if actions:
        lines.append("")
        lines.append("*Actions*")
        for a in actions:
            lines.append(f"\u2022 {esc(a)}")
    lines.append("")
    try:
        rnd = json.loads((REPO / "worldsim/worldsim_state.json").read_text()).get("round", "?")
    except Exception:
        rnd = "?"
    footer = f"round {rnd} \u00b7 full brief: status/BRIEF.md"
    lines.append("_" + esc(footer) + "_")
    text = "\n".join(lines)[:3800]

    ok, detail = api("sendMessage", {
        "chat_id": chat, "text": text,
        "parse_mode": "Markdown", "disable_web_page_preview": True,
    })
    if ok:
        STATE_FILE.write_text(fingerprint)
        print(f"sent to {chat} ({len(high)} high item(s))")
        return 0

    print(f"send failed: {detail}")
    return 1 if ("401" in detail or "409" in detail) else 2


if __name__ == "__main__":
    sys.exit(main())
