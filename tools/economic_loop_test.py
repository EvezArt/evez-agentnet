#!/usr/bin/env python3
"""Static safety test for the one-command economic loop."""
from pathlib import Path
p=Path(__file__).resolve().parent/"economic_loop.py"
s=p.read_text(encoding="utf-8")
for required in ["external_action_allowed", "human_approval_required", "opportunity_engine.py", "economic_spine.py", "economic_permasignal.py"]:
    assert required in s, required
assert "send outreach" in s.lower()
assert "moves money" in s.lower()
print("economic loop safety test: OK")
