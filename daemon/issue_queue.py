"""
daemon/issue_queue.py — evez-agentnet
GitHub Issues as task queue.
Resolves: evez-agentnet#15

Labels used:
  daemon-task     — pending task
  daemon-running  — in progress
  daemon-done     — completed
  daemon-failed   — failed

Env:
  GITHUB_TOKEN
  DAEMON_REPO   — default: EvezArt/evez-agentnet
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

log = logging.getLogger("daemon.issue_queue")

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO  = os.environ.get("DAEMON_REPO", "EvezArt/evez-agentnet")
API   = "https://api.github.com"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _gh(method: str, path: str, body: dict = None) -> dict:
    url  = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:300]}
    except Exception as e:
        return {"error": str(e)}


def dequeue(limit: int = 3) -> list:
    """Return up to `limit` open issues labeled daemon-task."""
    data = _gh("GET", f"/repos/{REPO}/issues?state=open&labels=daemon-task&per_page={limit}")
    if isinstance(data, list):
        return data
    return []


def mark_running(issue_number: int):
    _gh("POST", f"/repos/{REPO}/issues/{issue_number}/labels", {"labels": ["daemon-running"]})
    _remove_label(issue_number, "daemon-task")


def complete(issue_number: int, result_comment: str):
    _gh("POST", f"/repos/{REPO}/issues/{issue_number}/comments",
        {"body": f"✅ **DAEMON COMPLETE**\n\n{result_comment}"})
    _gh("PATCH", f"/repos/{REPO}/issues/{issue_number}",
        {"state": "closed", "state_reason": "completed"})
    _gh("POST", f"/repos/{REPO}/issues/{issue_number}/labels", {"labels": ["daemon-done"]})
    _remove_label(issue_number, "daemon-running")
    log.info(f"[queue] Closed issue #{issue_number} as done.")


def fail(issue_number: int, reason: str):
    _gh("POST", f"/repos/{REPO}/issues/{issue_number}/comments",
        {"body": f"❌ **DAEMON FAILED**\n\n{reason}"})
    _gh("POST", f"/repos/{REPO}/issues/{issue_number}/labels", {"labels": ["daemon-failed"]})
    _remove_label(issue_number, "daemon-running")
    log.warning(f"[queue] Issue #{issue_number} marked failed: {reason}")


def create_task(title: str, body: str) -> dict:
    """Create a new daemon-task issue (for self-building loop)."""
    return _gh("POST", f"/repos/{REPO}/issues",
               {"title": title, "body": body, "labels": ["daemon-task"]})


def _remove_label(issue_number: int, label: str):
    from urllib.parse import quote
    _gh("DELETE", f"/repos/{REPO}/issues/{issue_number}/labels/{quote(label)}")


def ensure_labels():
    """Create required labels if they don't exist."""
    labels = [
        {"name": "daemon-task",    "color": "0075ca", "description": "Pending daemon task"},
        {"name": "daemon-running", "color": "e4e669", "description": "Daemon processing"},
        {"name": "daemon-done",    "color": "0e8a16", "description": "Daemon completed"},
        {"name": "daemon-failed",  "color": "d93f0b", "description": "Daemon failed"},
    ]
    for lbl in labels:
        res = _gh("POST", f"/repos/{REPO}/labels", lbl)
        if res.get("error") == 422:
            pass  # already exists
