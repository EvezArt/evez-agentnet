# Entrypoint sovereignty

## Current hierarchy

1. `run_agentnet.py` — canonical launcher
2. `orchestrator_cognition_governed.py` — strongest runtime sovereignty path
3. `orchestrator_cognition_full.py` — cognition path with uncertainty + build queue
4. `orchestrator_cognition_native.py` — native merged cognition path
5. `orchestrator_with_cognition_rsi.py` — transitional wrapper path
6. `orchestrator.py` — legacy loop

## Meaning

The presence of older entrypoints does not make them sovereign.
Sovereignty is determined by the default boot path, governance gates, checkpoint lineage, and proof surface.

## Effective authority chain

`run_agentnet.py`
→ `orchestrator_cognition_governed.py`
→ daemon checkpoint + lineage
→ governed ship gate
→ proof surface

## Deprecation note

`orchestrator.py` still exists for compatibility, but it is not the preferred authority path.
Any new operational work should target the governed cognition-first entrypoint family.
