# EVEZ AgentNet — Multi-Agent Orchestration

Coordinates 8 autonomous agents across the EVEZ stack: SPINE, TRUNK, DEPLOY, VAULT, HARVEST, SCOUT, WITNESS, CAIN.

## Epistemic control plane

AgentNet now treats uncertainty as durable state rather than discarded prose.

- `schemas/capability.schema.json` defines capability lifecycle and provenance.
- `schemas/evez1-message.schema.json` defines the EVEZ/1 wire envelope.
- `schemas/reality-surface.schema.json` defines bounded observations of external surfaces.
- `docs/ACKNOWLEDGEMENT_SYSTEM.md` defines the acknowledgement and negative-space model.
- `docs/acknowledgements.jsonl` stores explicit boundaries, unresolved objects, and next experiments.
- `tools/acknowledgement_audit.py` validates that unresolved records remain unresolved and that observations carry evidence references.

The system distinguishes observation, support, inference, proposal, unknown, inaccessible, contradiction, staleness, and retraction. Configuration alone never upgrades a capability to effective or verified.

## Agents
| Agent | Role |
|-------|------|
| SPINE | Core coordination |
| TRUNK | Data pipeline management |
| DEPLOY | Automated deployment |
| VAULT | Security and encryption |
| HARVEST | Data collection and research |
| SCOUT | Intelligence gathering |
| WITNESS | Audit and compliance |
| CAIN | Contradiction detection |

## Quick Start

```bash
git clone https://github.com/EvezArt/evez-agentnet.git
cd evez-agentnet
pip install -r requirements.txt
python agentnet.py
```

---
*Part of EVEZ-OS*
