# EVEZ AgentNet — Multi-Agent Orchestration

Coordinates 8 autonomous agents across the EVEZ stack: SPINE, TRUNK, DEPLOY, VAULT, HARVEST, SCOUT, WITNESS, CAIN.

## Epistemic control plane

AgentNet treats uncertainty as durable state rather than discarded prose.

- `schemas/capability.schema.json` defines capability lifecycle and provenance.
- `schemas/evez1-message.schema.json` defines the EVEZ/1 wire envelope.
- `schemas/reality-surface.schema.json` defines bounded observations of external surfaces.
- `docs/ACKNOWLEDGEMENT_SYSTEM.md` defines the acknowledgement and negative-space model.
- `docs/acknowledgements.jsonl` stores explicit boundaries, unresolved objects, and next experiments.
- `tools/acknowledgement_audit.py` validates that unresolved records remain unresolved and that observations carry evidence references.

The system distinguishes observation, support, inference, proposal, unknown, inaccessible, contradiction, staleness, and retraction. Configuration alone never upgrades a capability to effective or verified.

## Economic acquisition spine

The economic layer is now executable and evidence-bound.

- `schemas/opportunity.schema.json`: normalized acquisition opportunity.
- `schemas/economic-event.schema.json`: append-only economic event contract.
- `tools/opportunity_engine.py`: converts authorized public observations into acquisition records.
- `tools/economic_spine.py`: hash-chained economic events.
- `tools/economic_reducer.py`: separates proposed, contracted, invoiced, received, and cost values.
- `docs/economy/live-opportunities-2026-09-19.jsonl`: current public opportunity observations.
- `docs/ECONOMIC_ACQUISITION.md`: state machine and provenance rules.

Economic truth boundary:

```
OPPORTUNITY -> OFFER -> CONTRACT -> DELIVERY -> INVOICE -> PAYMENT
```

A proposed dollar is not a contracted dollar. A contracted dollar is not an invoiced dollar. An invoiced dollar is not observed cash. The ledger records these as separate events.

External contact, contracts, invoicing, and money movement remain human-approved. The system can discover, normalize, verify, and prepare; it does not fabricate revenue or silently act on external parties.

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

Economic self-test:

```bash
python tools/economic_spine_test.py
python tools/economic_spine.py --ledger docs/economy/economic-events.jsonl verify
python tools/economic_spine.py --ledger docs/economy/economic-events.jsonl money
```

---

*Part of EVEZ-OS*
