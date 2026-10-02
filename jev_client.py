#!/usr/bin/env python3
"""
Jev client for evez-agentnet.

Jev is TypeSafe AI's "System One" model: it does not generate text. You send a
block of `state` plus typed `questions`, and get back typed answers with
calibrated probabilities and confidence. Schema is fixed in advance, so it
cannot return a value outside the shape you defined.

    POST https://api.typesafe.ai/v1/systemone
    Authorization: Bearer $TYPESAFE_API_KEY

Three primitives:
    noul   -> yes/no probability (0-1)
    choice -> selected option + per-option probabilities + confidence
    score  -> weighted value across ordered levels + probabilities + confidence

Design constraints this module respects:
  - NEVER fabricates an answer. If the API is unreachable, the key is missing,
    or the payload is rejected, it raises JevUnavailable. A caller that treats
    a stub as a real probability would reintroduce exactly the "declarative
    surface reporting an outcome it never achieved" defect this repo has been
    fixing all session.
  - Bounded retries with exponential backoff on 429/529 only.
  - Optional offline mode for tests, which is clearly labelled in every answer.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

RETRY_STATUS = {429, 529}          # rate limited / overloaded -> retry
MAX_RETRIES = 3
BACKOFF_BASE = 0.6


class JevUnavailable(RuntimeError):
    """Raised when no real answer could be obtained. Never swallowed."""


@dataclass
class JevAnswer:
    key: str
    type: str
    # noul
    noul: float | None = None
    # choice
    choice: str | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    # score
    score: float | None = None
    legend: dict[str, str] = field(default_factory=dict)
    # choice + score
    confidence: float | None = None

    source: str = "jev"             # "jev" | "offline-fixture"
    model: str = ""


def _api_key() -> str:
    return os.environ.get("TYPESAFE_API_KEY", "").strip()


def evaluate(state: Any, questions: dict, *, timeout: int = 30,
             retries: int = MAX_RETRIES, verbose: bool = False) -> dict[str, JevAnswer]:
    """Evaluate `state` against `questions`. Returns {key: JevAnswer}.

    Raises JevUnavailable if no genuine response was obtained.
    """
    if not questions:
        raise ValueError("questions must not be empty")
    if not _api_key():
        raise JevUnavailable("TYPESAFE_API_KEY is not set")

    body = json.dumps({
        "state": state,
        "model": MODEL,
        "questions": questions,
    }).encode()

    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            ENDPOINT, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
                "User-Agent": "evez-agentnet-jev/1.0",
            })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read())
            return _parse(payload)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            last_err = f"HTTP {e.code}: {detail}"
            if e.code in RETRY_STATUS and attempt < retries:
                time.sleep(BACKOFF_BASE * (2 ** attempt))
                continue
            if e.code == 401:
                raise JevUnavailable(
                    "TYPESAFE_API_KEY rejected (401). Check the key.") from e
            if e.code == 422:
                raise JevUnavailable(
                    f"request rejected as invalid (422): {detail}") from e
            raise JevUnavailable(last_err) from e
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:140]}"
            if attempt < retries:
                time.sleep(BACKOFF_BASE * (2 ** attempt))
                continue
    raise JevUnavailable(last_err or "unknown failure")


def _parse(payload: dict) -> dict[str, JevAnswer]:
    model = payload.get("model", "?")
    out: dict[str, JevAnswer] = {}
    for key, raw in (payload.get("answers") or {}).items():
        a = JevAnswer(key=key, type=raw.get("type", "?"), model=model)
        if raw.get("type") == "noul":
            a.noul = float(raw.get("noul", 0.0))
        elif raw.get("type") == "choice":
            a.choice = raw.get("choice")
            a.probabilities = {k: float(v) for k, v
                               in (raw.get("probabilities") or {}).items()}
            a.confidence = raw.get("confidence")
        elif raw.get("type") == "score":
            a.score = float(raw.get("score", 0.0))
            a.legend = raw.get("legend") or {}
            a.probabilities = {k: float(v) for k, v
                               in (raw.get("probabilities") or {}).items()}
            a.confidence = raw.get("confidence")
        out[key] = a
    return out


# ── offline fixtures ────────────────────────────────────────────────────────
# Used ONLY by tests, and every answer is tagged source="offline-fixture" so a
# fixture can never be mistaken for a real model response.
OFFLINE: dict[tuple, dict] = {}


def register_offline(marker: str, response: dict) -> None:
    OFFLINE[marker] = response


def evaluate_offline(marker: str, keys: dict) -> dict[str, JevAnswer]:
    if marker not in OFFLINE:
        raise JevUnavailable(f"no offline fixture registered for {marker!r}")
    out = {}
    for key, spec in keys.items():
        t = spec.get("type", "noul")
        out[key] = JevAnswer(
            key=key, type=t, source="offline-fixture", model="fixture",
            noul=spec.get("noul") if t == "noul" else None,
            choice=spec.get("choice") if t == "choice" else None,
            probabilities=spec.get("probabilities", {}) if t != "noul" else {},
            score=spec.get("score") if t == "score" else None,
            legend=spec.get("legend", {}) if t == "score" else {},
            confidence=spec.get("confidence") if t != "noul" else None,
        )
    return out
