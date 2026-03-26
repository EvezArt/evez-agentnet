"""Living cognition daemon package for evez-agentnet.

This package provides a restartable cognition kernel built around:
- checkpointed ontology and law state
- unresolved branch preservation
- identity attractor tracking
- self-evaluation and revision loops
- executive arbitration and build queue emission
"""

from .daemon import LivingLogicDaemon
from .models import Branch, CognitionState, IdentityAttractor, ValuationCircuit

__all__ = [
    "LivingLogicDaemon",
    "Branch",
    "CognitionState",
    "IdentityAttractor",
    "ValuationCircuit",
]
