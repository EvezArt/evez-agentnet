# START HERE — evez-agentnet governed runtime

If you are opening this repo cold, start here instead of assuming `orchestrator.py` is still the real authority path.

## What this repo is now

`evez-agentnet` is a **governed cognition-first agent runtime** for:

- scanning live signals
- ranking and preserving rival futures
- generating artifacts from both predictions and daemon build queues
- shipping only when cognition gates permit it
- emitting proof, receipt, dashboard, and spine-digest artifacts every round

It is no longer just a flat scan → predict → generate → ship loop.

## Canonical boot path

```bash
python run_agentnet_supervised.py
```

That path runs:

```text
run_agentnet_supervised.py
→ orchestrator_cognition_governed.py
→ LivingLogicDaemon checkpoint + lineage
→ cognition-aware predictor
→ build-queue-aware generator
→ cognition-governed shipper
→ RSI branch injection
→ proof / receipt / dashboard surfaces
```

## Best use cases

### Signal-to-artifact commerce
Use the runtime to turn live signals into reports, threads, products, code posts, and build artifacts.

### Controlled autonomous operation
Use it when you want autonomy that can pause, investigate, or refuse to ship under uncertainty.

### Rival-future forecasting
Use it when preserving ambiguity matters more than forcing one prediction too early.

### Provenance-heavy multi-agent systems
Use it when lineage hashes, checkpoints, ship-gate reasons, and proof artifacts must exist by default.

### Long-running cognition experiments
Use it when the point is a restartable inference organism, not just a content loop.

## What makes it different in this race

Most systems in this lane still look like one of these:

1. pipeline agents  
2. chat wrappers with tools  
3. multi-agent theater  
4. confidence-score autonomy  

`evez-agentnet` differs because:

- uncertainty is part of runtime state, not decorative logging
- RSI hypotheses get pushed back into cognition as branches
- build pressure and opportunistic ranking are separated
- shipping is subordinated to action mode, unresolved residue, and entropy
- proof, receipt, dashboard, and spine digest surfaces exist as first-class artifacts
- there is a clear authority chain instead of loose agent vibes

## Current authority hierarchy

1. `run_agentnet_supervised.py`
2. `run_agentnet.py`
3. `orchestrator_cognition_governed.py`
4. `orchestrator_cognition_full.py`
5. `orchestrator_cognition_native.py`
6. `orchestrator_with_cognition_rsi.py`
7. `orchestrator.py` (legacy compatibility)

## Quick commands

Supervised runtime:

```bash
python run_agentnet_supervised.py
```

Single governed round:

```bash
AGENTNET_MODE=governed python run_agentnet_once.py
```

Proof:

```bash
AGENTNET_MODE=proof python run_agentnet.py
```

Receipt:

```bash
python cognition_receipt.py
```

Governed dashboard:

```bash
python cognition_dashboard_governed.py
```

Spine digest:

```bash
python cognition_spine_digest.py
```
