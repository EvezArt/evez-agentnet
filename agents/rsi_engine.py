"""
RSI Hypothesis Engine — evez-agentnet
======================================
Standalone module. Generates, evaluates, and evolves 3 RSI hypotheses
per OODA cycle. Hypotheses can be accepted, rejected, or forked into
sub-agents for parallel testing.
"""

import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Hypothesis:
    id: str
    text: str
    round_born: int
    evidence_for: int = 0
    evidence_against: int = 0
    accepted: bool = False
    rejected: bool = False
    forked: bool = False
    children: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        total = self.evidence_for + self.evidence_against
        return self.evidence_for / total if total > 0 else 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "round_born": self.round_born,
            "confidence": round(self.confidence, 3),
            "accepted": self.accepted,
            "rejected": self.rejected,
            "forked": self.forked,
            "children": self.children,
        }


class RSIEngine:
    """
    RSI (Recursive Self-Improvement) Hypothesis Engine.
    Generates 3 hypotheses per round, tests them against observations,
    and evolves the most promising ones.
    """

    STORE = Path("worldsim/rsi_hypotheses.jsonl")

    def __init__(self, round_num: int, state: dict):
        self.round = round_num
        self.state = state
        self.hypotheses: list[Hypothesis] = []
        self.STORE.parent.mkdir(exist_ok=True)

    def generate(self) -> list[Hypothesis]:
        """Generate exactly 3 hypotheses tuned to current system state."""
        s = self.state
        agents = s.get("agents", {})
        maes = s.get("maes", {})
        rnd = self.round

        rep = {k: v.get("reputation", 0.9) for k, v in agents.items()}
        # Only prescribe recovery for an agent that is actually below the
        # canonical threshold. Picking min() unconditionally made a saturated
        # (rep=1.00) agent the target of "recover via streak" every round.
        below = {k: v for k, v in rep.items() if v < 0.80}
        players = maes.get("player_count", 0)
        fire_total = maes.get("fire_events_total", 0)

        if below:
            lowest_agent = min(below, key=below.get)
            lowest_rep = below[lowest_agent]
            h1_text = (
                f"Inject synthetic success task into '{lowest_agent}' agent "
                f"(rep={lowest_rep:.2f}) to trigger streak recovery and push "
                f"above CANONICAL threshold ({0.80})."
            )
        else:
            floor = min(rep.values()) if rep else 0.9
            top = max(rep, key=rep.get) if rep else "scanner"
            idle = [k for k, v in agents.items() if not v.get("tasks_completed", 0)]
            if idle:
                h1_text = (
                    f"All agents at or above CANONICAL threshold (min={floor:.2f}) — "
                    f"'{idle[0]}' has completed 0 tasks despite "
                    f"rep={rep.get(idle[0], 0.9):.2f}; widen its task surface instead "
                    f"of manufacturing recovery."
                )
            else:
                h1_text = (
                    f"All agents at or above CANONICAL threshold (min={floor:.2f}, "
                    f"leader '{top}') — hold steady, no recovery warranted."
                )

        self.hypotheses = [
            Hypothesis(id=f"h{rnd}-1", text=h1_text, round_born=rnd),
            Hypothesis(
                id=f"h{rnd}-2",
                text=(
                    f"MAES ecology: {players} verified players detected. "
                    f"{'Scale NPC count by 2x and diversify behaviour trees.' if players >= 5 else 'Emit Turing-challenge FIRE events to verify unclassified agents.'}"
                ),
                round_born=rnd,
            ),
            Hypothesis(
                id=f"h{rnd}-3",
                # Zero FIRE events is the absence of a signal, not a reason to
                # widen the compassion aperture. Expanding on 0 events produced
                # the inverted directive seen in production logs.
                text=(
                    f"Moral registry evolution (round {rnd}): {fire_total} cumulative FIRE events → "
                    + (
                        "expand compassion_layer weight by +0.05; anticipate external suffering "
                        "signals from oracle bridge and pre-load empathic response templates."
                        if fire_total > 0
                        else "hold compassion_layer weight — no FIRE signal to respond to."
                    )
                ),
                round_born=rnd,
            ),
        ]
        return self.hypotheses

    def evaluate(self, hypothesis: Hypothesis, test_fn: Callable[[Hypothesis], bool]) -> Hypothesis:
        """Run a test function against a hypothesis and update evidence."""
        try:
            passed = test_fn(hypothesis)
            if passed:
                hypothesis.evidence_for += 1
                if hypothesis.confidence >= 0.75:
                    hypothesis.accepted = True
            else:
                hypothesis.evidence_against += 1
                if hypothesis.confidence <= 0.25 and (hypothesis.evidence_for + hypothesis.evidence_against) >= 4:
                    hypothesis.rejected = True
        except Exception as e:
            hypothesis.evidence_against += 1
        return hypothesis

    def fork(self, hypothesis: Hypothesis, sub_id: str) -> Hypothesis:
        """Fork a hypothesis into a named sub-agent variant."""
        child = Hypothesis(
            id=f"{hypothesis.id}-fork-{sub_id}",
            text=f"[FORK of {hypothesis.id}] {hypothesis.text}",
            round_born=self.round,
        )
        hypothesis.children.append(child.id)
        hypothesis.forked = True
        self.hypotheses.append(child)
        return child

    def persist(self):
        """Append all hypotheses to JSONL store."""
        with open(self.STORE, "a") as f:
            for h in self.hypotheses:
                f.write(json.dumps({"ts": time.time(), **h.to_dict()}) + "\n")

    def summary(self) -> list[dict]:
        return [h.to_dict() for h in self.hypotheses]
