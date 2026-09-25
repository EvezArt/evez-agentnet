# Economic PermaSignal Bridge

Economic events are converted into semantic human-state signals for the existing EVEZ-HSM/1 communication layer.

```
ECONOMIC EVENT
    |
    v
CLASSIFY / ACKNOWLEDGE
    |
    v
PERMASIGNAL
    |
    +--> COMMIT when an economic state is observed/supported
    |
    +--> REVISE when contradicted/stale/retracted
```

This bridge does not authorize external action and does not turn a proposed amount into observed money. It makes the economic transition legible to the same human-state machine used by the evidence architecture.

Command:

```bash
python tools/economic_permasignal.py --ledger docs/economy/economic-events.jsonl
```
