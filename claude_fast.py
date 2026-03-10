#!/usr/bin/env python3
"""
claude_fast.py — Lightweight Claude runtime.
Fast path: single witness, no consensus overhead.
Falls back to L1 multi-witness on uncertainty or high-stakes flags.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Lane = Literal["fast", "consensus", "forced_consensus"]


@dataclass
class FastResult:
    content: str
    lane_used: Lane
    model: str
    latency_ms: float
    evidence_hash: str
    timestamp: str
    escalated: bool
    escalation_reason: str | None = None
    warning: str | None = None


DEFAULT_MODEL = "claude-sonnet-4-5"
FAST_MAX_TOKENS = 1024
CONSENSUS_TRIGGERS = [
    "deploy",
    "delete",
    "merge",
    "ship",
    "approve",
    "override",
    "bypass",
    "grant",
    "revoke",
    "execute",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _needs_consensus(prompt: str, force: bool) -> tuple[bool, str | None]:
    """Decide if this prompt must go to L1 multi-witness."""
    if force:
        return True, "caller_forced"

    prompt_lower = prompt.lower()
    for trigger in CONSENSUS_TRIGGERS:
        if trigger in prompt_lower:
            return True, f"trigger_word:{trigger}"

    return False, None


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _run_l1_consensus(prompt: str, system: str | None) -> dict:
    layer1_witness = importlib.import_module("layer1_witness")
    run_l1_consensus = getattr(layer1_witness, "run_l1_consensus")
    return run_l1_consensus(prompt, system=system)


def _fallback_content(prompt: str, reason: str) -> str:
    """Guaranteed no-network fallback so the runtime always returns a result."""
    preview = prompt.strip().replace("\n", " ")[:240]
    return (
        "[claude_fast fallback] Claude request unavailable. "
        f"Reason: {reason}. Prompt preview: {preview}"
    )


def _call_claude(
    prompt: str,
    system: str | None,
    model: str,
    max_tokens: int,
) -> tuple[str, float]:
    """Raw Claude API call. Returns (content, latency_ms)."""
    if not _has_module("anthropic"):
        raise RuntimeError("anthropic package not installed: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    anthropic = importlib.import_module("anthropic")
    client = anthropic.Anthropic(api_key=api_key)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    latency_ms = (time.monotonic() - t0) * 1000.0

    # Anthropic responses return content blocks; first text block is sufficient here.
    content = response.content[0].text
    return content, latency_ms


def ask(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = FAST_MAX_TOKENS,
    force_consensus: bool = False,
) -> FastResult:
    """
    Fast path: call Claude directly.
    Auto-escalates to L1 consensus on trigger words or force flag.
    """
    escalate, reason = _needs_consensus(prompt, force_consensus)

    if escalate and _has_module("layer1_witness"):
        t0 = time.monotonic()
        consensus_result = _run_l1_consensus(prompt, system=system)
        latency_ms = (time.monotonic() - t0) * 1000.0

        content = consensus_result.get("answer", str(consensus_result))
        lane_used: Lane = "forced_consensus" if force_consensus else "consensus"
        return FastResult(
            content=content,
            lane_used=lane_used,
            model="l1_multi_witness",
            latency_ms=latency_ms,
            evidence_hash=_hash(content),
            timestamp=_now_utc(),
            escalated=True,
            escalation_reason=reason,
        )

    warning = None
    if escalate and not _has_module("layer1_witness"):
        warning = "consensus requested but layer1_witness unavailable; using fast lane"

    try:
        content, latency_ms = _call_claude(prompt, system, model, max_tokens)
    except Exception as exc:
        latency_ms = 0.0
        warning = f"{warning + '; ' if warning else ''}Claude API unavailable ({exc})"
        content = _fallback_content(prompt, str(exc))

    return FastResult(
        content=content,
        lane_used="fast",
        model=model,
        latency_ms=latency_ms,
        evidence_hash=_hash(content),
        timestamp=_now_utc(),
        escalated=False,
        escalation_reason=reason if warning and escalate else None,
        warning=warning,
    )


def ask_json(prompt: str, **kwargs) -> dict:
    """Same as ask() but returns dict for easy downstream use."""
    result = ask(prompt, **kwargs)
    return asdict(result)


def append_spine_event(prompt: str, result: FastResult, spine_path: str = "spine/spine.jsonl") -> dict:
    """Append Claude runtime evidence to the local EVEZ spine event log."""
    path = Path(spine_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": _now_utc(),
        "type": "claude_fast_result",
        "data": {
            "prompt_hash": _hash(prompt),
            "result": asdict(result),
        },
    }
    hashed = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    payload["sha256"] = hashed
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight Claude runtime")
    parser.add_argument("prompt", nargs="?", help="Prompt text")
    parser.add_argument("--system", default=None, help="System prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=FAST_MAX_TOKENS)
    parser.add_argument("--force-consensus", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output full JSON")
    parser.add_argument("--spine-log", default=None, help="Optional path to append runtime event JSONL")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        parser.print_help()  # pragma: no cover
        return 1

    result = ask(
        prompt,
        system=args.system,
        model=args.model,
        max_tokens=args.max_tokens,
        force_consensus=args.force_consensus,
    )

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(result.content)
        print(
            f"\n[{result.lane_used} | {result.latency_ms:.0f}ms | {result.evidence_hash}]",
            file=sys.stderr,
        )

    if args.spine_log:
        append_spine_event(prompt, result, spine_path=args.spine_log)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
