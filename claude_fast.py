#!/usr/bin/env python3
"""
claude_fast.py — Lightweight Claude runtime.
Fast path: single witness, no consensus overhead.
Falls back to L1 multi-witness on uncertainty or high-stakes flags.
"""

import argparse
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

# Optional heavy path
try:
    from layer1_witness import run_l1_consensus

    HAS_L1 = True
except ImportError:
    HAS_L1 = False

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

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
    escalation_reason: Optional[str] = None


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


def _needs_consensus(prompt: str, force: bool) -> tuple[bool, Optional[str]]:
    """Decide if this prompt must go to L1 multi-witness."""
    if force:
        return True, "caller_forced"

    prompt_lower = prompt.lower()
    for trigger in CONSENSUS_TRIGGERS:
        if trigger in prompt_lower:
            return True, f"trigger_word:{trigger}"

    return False, None


def _call_claude(
    prompt: str,
    system: Optional[str],
    model: str,
    max_tokens: int,
) -> tuple[str, float]:
    """Raw Claude API call. Returns (content, latency_ms)."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    messages = [{"role": "user", "content": prompt}]
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    latency_ms = (time.monotonic() - t0) * 1000

    content = response.content[0].text
    return content, latency_ms


def ask(
    prompt: str,
    system: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = FAST_MAX_TOKENS,
    force_consensus: bool = False,
) -> FastResult:
    """
    Fast path: call Claude directly.
    Auto-escalates to L1 consensus on trigger words or force flag.
    """
    escalate, reason = _needs_consensus(prompt, force_consensus)

    if escalate and HAS_L1:
        t0 = time.monotonic()
        consensus_result = run_l1_consensus(prompt, system=system)
        latency_ms = (time.monotonic() - t0) * 1000

        content = consensus_result.get("answer", str(consensus_result))
        return FastResult(
            content=content,
            lane_used="forced_consensus" if force_consensus else "consensus",
            model="l1_multi_witness",
            latency_ms=latency_ms,
            evidence_hash=_hash(content),
            timestamp=_now_utc(),
            escalated=True,
            escalation_reason=reason,
        )

    content, latency_ms = _call_claude(prompt, system, model, max_tokens)
    return FastResult(
        content=content,
        lane_used="fast",
        model=model,
        latency_ms=latency_ms,
        evidence_hash=_hash(content),
        timestamp=_now_utc(),
        escalated=False,
        escalation_reason=None,
    )


def ask_json(prompt: str, **kwargs) -> dict:
    """Same as ask() but returns dict for easy downstream use."""
    result = ask(prompt, **kwargs)
    return asdict(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lightweight Claude runtime")
    parser.add_argument("prompt", nargs="?", help="Prompt text")
    parser.add_argument("--system", default=None, help="System prompt")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=FAST_MAX_TOKENS)
    parser.add_argument("--force-consensus", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output full JSON")
    args = parser.parse_args()

    prompt = args.prompt or os.sys.stdin.read().strip()
    if not prompt:
        parser.print_help()
        raise SystemExit(1)

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
            file=os.sys.stderr,
        )
