# Canonical run surface

Use `run_agentnet.py` as the canonical launcher.

## Default behavior

Without environment overrides, the launcher boots the governed cognition-first path:

```bash
python run_agentnet.py
```

This dispatches to:

- `orchestrator_cognition_governed.py`

## Optional modes

```bash
AGENTNET_MODE=legacy python run_agentnet.py
AGENTNET_MODE=native python run_agentnet.py
AGENTNET_MODE=full python run_agentnet.py
AGENTNET_MODE=governed python run_agentnet.py
AGENTNET_MODE=status python run_agentnet.py
AGENTNET_MODE=proof python run_agentnet.py
```

## Proof and dashboard

```bash
AGENTNET_MODE=proof python run_agentnet.py
python cognition_dashboard.py
```

The dashboard writes:

- `proof/latest_runtime_dashboard.html`

## Governance intent

Legacy entrypoints still exist, but they are no longer the preferred sovereignty path.
The default run surface now points at the cognition-governed loop.
