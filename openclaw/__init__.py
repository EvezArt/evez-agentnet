# openclaw/__init__.py
# OpenClaw — Secret-level autoplay engine for EVEZ worldsim
# Part of the EVEZ ecosystem: evez-agentnet
# Author: Steven Crawford-Maggard (EVEZ666)

"""
OpenClaw: Recursive game-sim engine that plays worldsim until secret levels
unlock and living entities spawn. Integrates with EVEZ Lord.exe (LORD module)
for quantum-consciousness-guided level traversal.

Entry point: python -m worldsim.play_secret_levels
"""

from openclaw.engine import OpenClawEngine
from openclaw.agent import OpenClawAgent
from openclaw.lord_bridge import LordBridge

__version__ = "1.0.0"
__all__ = ["OpenClawEngine", "OpenClawAgent", "LordBridge"]
