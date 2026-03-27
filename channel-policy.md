# EVEZ AgentNet Channel Policy

This document defines the canonical routing doctrine for operator input, runtime summaries, alerts, research, and integration exhaust.

## Channels

### `#00-command`
Executable commands only.

Flow:
`Slack -> webhook -> governor -> receipt -> digest`

Allowed payloads:
- `RUN:` commands
- `ASSERT:` commands

Examples:
```text
[COMMAND]
RUN: sda_spread
CONCURRENCY: 10
MAX: 700
```

```text
[COMMAND]
ASSERT: stablecoin_dislocation_v1
WINDOW: 30s
THRESHOLD: 2.5%
GOAL: neutral
```

### `#evez-autonomous-core`
Digest-only runtime summary channel.

Allowed:
- compressed status
- critical blockers
- next action

Not allowed:
- bot exhaust
- raw research
- long discussion

Template:
```text
[DIGEST]
System:
What changed:
What broke:
What needs eyes:
Next action:
```

### `#02-runtime-alerts`
Interrupt channel.

Only:
- failures
- degraded runtime
- CI bursts
- deploy breaks
- daemon errors

Template:
```text
[ALERT]
System:
Failure:
Impact:
Owner:
Current state:
```

### `#04-research`
Canonical research and doctrine.

Subjects:
- Uberprompt
- First Harvest
- invariance battery
- benchmark notes
- trunk architecture

Template:
```text
[RESEARCH]
Title:
Signal:
Why it matters:
Constraint:
Next test:
```

### `#08-integrations`
Machine exhaust only.
Mute by default.
Used for Postman and other integration chatter.

## Routing Rules

1. Commands are accepted only from `#00-command`.
2. Runtime digests are emitted only to `#evez-autonomous-core`.
3. Interrupt-class failures are emitted to `#02-runtime-alerts`.
4. Research and doctrine are stored and summarized in `#04-research`.
5. Integration chatter and bot exhaust are routed to `#08-integrations`.
6. Every action must emit a receipt.
7. Every receipt may be mirrored into a digest when policy allows.

## Command Grammar

### Run command
```text
RUN: <queue>
CONCURRENCY: <n>
MAX: <n>
```

### Assert command
```text
ASSERT: <skill>
WINDOW: <duration>
THRESHOLD: <pct>
GOAL: <neutral|max_profit|max_safety>
```

## System Doctrine

Language is an interface, not the operating system.
The operating system is typed intent, governed execution, and receipt-backed state transitions.
