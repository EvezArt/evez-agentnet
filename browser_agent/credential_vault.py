#!/usr/bin/env python3
"""
evez-agentnet/browser_agent/credential_vault.py

Read credentials from env / write back to GitHub Actions secrets.
Used by browser_agent tasks to persist newly retrieved API keys.
"""
import os
import json
import base64
import logging
import urllib.request
from typing import Optional

import nacl.public

log = logging.getLogger("agentnet.browser_agent.vault")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "EvezArt")
REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "evez-agentnet")


def get(key: str) -> Optional[str]:
    """Read a secret from environment."""
    return os.environ.get(key)


def set_github_secret(secret_name: str, secret_value: str) -> bool:
    """
    Encrypt and write a secret to GitHub Actions repo secrets.
    Returns True on success.
    """
    if not GITHUB_TOKEN:
        log.warning("GITHUB_TOKEN not set — cannot write secret")
        return False
    try:
        pub_key, key_id = _get_public_key()
        encrypted = _encrypt(pub_key, secret_value)
        _put_secret(secret_name, encrypted, key_id)
        log.info(f"Secret {secret_name} written to GitHub Actions")
        return True
    except Exception as e:
        log.error(f"Failed to write secret {secret_name}: {e}")
        return False


def _get_public_key() -> tuple:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/public-key"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    return base64.b64decode(data["key"]), data["key_id"]


def _encrypt(public_key_bytes: bytes, secret_value: str) -> str:
    pub_key = nacl.public.PublicKey(public_key_bytes)
    sealed = nacl.public.SealedBox(pub_key)
    encrypted = sealed.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def _put_secret(name: str, encrypted_value: str, key_id: str):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/{name}"
    body = json.dumps({"encrypted_value": encrypted_value, "key_id": key_id}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        pass  # 201 Created or 204 No Content = success
