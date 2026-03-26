# Run the cognition-first orchestrator

Use this entrypoint when you want the scan → predict → generate → ship loop to be gated by the restartable cognition daemon.

```bash
python orchestrator_with_cognition.py
```

Optional environment variables:

- `COGNITION_STATE_DIR=.state`
- `ROUND_INTERVAL=1800`
- `MAES_ENABLED=1`
- `OPENCLAW_ENABLED=1`

## Behavior

The wrapper does this each round:

1. runs MAES observe tick
2. runs scan
3. feeds scan summary into `LivingLogicDaemon`
4. appends daemon checkpoint + lineage hash into the spine
5. gates generate / ship behavior by `action_mode`
6. closes the round with the existing RSI + OpenClaw flow
