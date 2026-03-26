from __future__ import annotations

from dataclasses import asdict
from math import log
from typing import Any

from .models import Branch, utc_now

HEDGE_TERMS = {"may", "might", "could", "hypothesis", "if", "anticipate", "project", "likely"}
HIGH_CONSEQUENCE_TERMS = {"scale", "spawn", "unlock", "bridge", "recover", "evolve", "compassion", "player", "agent"}
DARK_PRESSURE_TERMS = {"moral", "suffering", "entropy", "wormhole", "recursive", "future", "intent", "ecology"}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def hypothesis_to_branch(label: str, hypothesis: str, round_no: int) -> Branch:
    lower = hypothesis.lower()
    hedge_count = sum(term in lower for term in HEDGE_TERMS)
    consequence_hits = sum(term in lower for term in HIGH_CONSEQUENCE_TERMS)
    dark_hits = sum(term in lower for term in DARK_PRESSURE_TERMS)

    plausibility = _bounded(0.42 - 0.03 * hedge_count + 0.02 * ("reputation" in lower) + 0.02 * ("player" in lower))
    consequence = _bounded(0.45 + 0.07 * consequence_hits)
    collapse_risk = _bounded(0.48 + 0.06 * hedge_count + 0.04 * ("evolve" in lower) + 0.03 * ("spawn" in lower))
    resonance = _bounded(0.4 + 0.06 * dark_hits + 0.04 * ("reputation" in lower) + 0.03 * ("round" in lower))

    notes = [
        f"source:rsi",
        f"round:{round_no}",
        "preserve rival future",
    ]
    if collapse_risk >= 0.6:
        notes.append("increase ambiguity retention")
    if consequence >= 0.65:
        notes.append("high consequence branch")
    if dark_hits:
        notes.append("dark pressure candidate")

    return Branch(
        label=label,
        plausibility=plausibility,
        consequence=consequence,
        collapse_risk=collapse_risk,
        resonance=resonance,
        notes=notes,
    )


def branch_entropy(branches: list[Branch]) -> float:
    priorities = [max(branch.priority, 1e-6) for branch in branches]
    total = sum(priorities)
    probs = [value / total for value in priorities]
    return -sum(p * log(p) for p in probs)


def inject_rsi_hypotheses(daemon: Any, hypotheses: list[str], round_no: int) -> dict[str, Any]:
    injected: list[dict[str, Any]] = []
    for index, hypothesis in enumerate(hypotheses, start=1):
        label = f"rsi-branch-{round_no}-{index}"
        branch = hypothesis_to_branch(label=label, hypothesis=hypothesis, round_no=round_no)
        daemon.state.branches.append(branch)
        injected.append(asdict(branch))

        if branch.collapse_risk >= 0.6:
            daemon.state.unresolved_residue.append(f"RSI:{hypothesis}")
        if branch.resonance >= 0.58:
            daemon.state.dark_state_pressure.append(f"RSI:{hypothesis}")

    entropy = branch_entropy(daemon.state.branches)
    unresolved_count = len(daemon.state.unresolved_residue)
    daemon.state.self_model["rsi_branch_entropy"] = round(entropy, 6)
    daemon.state.self_model["rsi_last_injected_at"] = utc_now()

    if unresolved_count >= 5:
        daemon.state.self_model["action_mode"] = "evidence_seek"

    daemon._log(
        "rsi_branch_injection",
        {
            "round": round_no,
            "hypothesis_count": len(hypotheses),
            "branches": injected,
            "entropy": entropy,
            "unresolved_count": unresolved_count,
            "dark_pressure_count": len(daemon.state.dark_state_pressure),
        },
    )

    return {
        "round": round_no,
        "hypothesis_count": len(hypotheses),
        "entropy": entropy,
        "unresolved_count": unresolved_count,
        "dark_pressure_count": len(daemon.state.dark_state_pressure),
        "branches": injected,
    }
