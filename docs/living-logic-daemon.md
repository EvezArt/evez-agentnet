# Living Logic Daemon scaffold for `evez-agentnet`

This subtree is designed to sit next to the existing ORS layer already present in the repo.

## What it adds

The repo already has a reasoning spine in `ors/`. This scaffold adds a stateful runtime layer:

- boot from latest checkpoint instead of waking blank
- preserve unresolved residue instead of flattening everything into false certainty
- track identity attractors (`observer`, `auditor`, `builder`)
- checkpoint ontology, laws, branches, and dark-state pressure after every step
- reopen unfinished cognitive residue on next start

## File map

```text
cognition/
  __init__.py
  models.py
  checkpoint.py
  executive.py
  ors_bridge.py
  lineage.py
  buildloop.py
  daemon.py
run_cognition_daemon.py
```

## Integration targets inside the current repo

The repo README describes:

- `scanner/`
- `predictor/`
- `generator/`
- `shipper/`
- `worldsim/`
- `spine/`
- `orchestrator.py`

The cleanest integration path is:

1. instantiate `LivingLogicDaemon` at orchestrator startup
2. feed scanner outputs into `daemon.step(...)`
3. use `active_identity` to bias which agent acts next
4. mirror checkpoints into the repo's existing provenance spine
5. use unresolved residue as a work queue for evidence-seeking runs

## Example

```bash
python run_cognition_daemon.py --state-dir .state --input "deploying a builder identity requires preserving unresolved risk branches"
```
