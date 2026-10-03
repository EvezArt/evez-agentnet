# EVEZ Swarm Selfie

A self-portrait of the swarm, generated from its own telemetry.

A selfie needs eyes. A swarm has none — no single vantage point from which to
look at itself. This is the nearest honest equivalent: a face assembled
entirely from operational state, where the expression is *derived* rather than
drawn.

## What you are looking at

| Feature | Source | Meaning |
|---|---|---|
| **Eyes** — one iris per agent | `agent_reputations` in the last `round_end` | Iris radius = reputation. A saturated agent is a wide pupil; a dead agent is a red ✕ |
| **Brows** — press downward | `rsi_branch_entropy` | More branching hypotheses, more weight between the eyes |
| **Nose ridge** | `predictor_entropy` | How little the predictor can resolve |
| **Mouth** | `earned_usd` per `round_end` | The revenue ledger, on its own axis. A zero series renders as a straight line at zero — it is **not** rescaled to look interesting |
| **Jaw** | service fleet uptime | A slack jaw is a fleet with failures |
| **Sutures** | `stack_health` warnings | The standing warnings, drawn on the jaw |
| **Halo** | `spine/spine.jsonl` | One link per verified hash-chain entry |

## Why the mouth is flat

Because the ledger is. `$0.00` lifetime across 1,961 spine entries, while the
swarm ships 246 times and every shipping agent except `shipper` sits at
reputation 1.0. The face is not sad by styling — it is flat because the
revenue is, and `shipper` (rep 0.00, streak 0) is the ✕ in the right eye.

That is the point of the artifact: it makes the gap between a swarm that is
*working* and a swarm that is *earning* visible in one glance, without anyone
having to read a dashboard.

## Run

```bash
python3 swarm_portrait.py            # -> swarm_portrait.html + swarm_portrait.png
python3 swarm_portrait.py --json     # just the measured state
python3 swarm_portrait.py --no-png   # skip the screenshot
python3 test_swarm_portrait.py       # 28 checks, must pass
```

The PNG is produced by headless Chrome from the self-contained HTML — a selfie
that only exists as markup is not a selfie.

## Design rules this file obeys

1. **No decoration.** Every mark is read from a file. Nothing is asserted that
   the state does not support.
2. **Zero renders as zero.** A flat series is not rescaled into a dramatic
   curve. The unflattering picture is the accurate one.
3. **No confident face from broken data.** A missing or torn spine yields no
   agents and no portrait, rather than an invented one.
4. **Derived, not drawn.** Change the telemetry and the expression changes.
   The self-test proves this by rendering divergent states and diffing them.

## Self-test

`test_swarm_portrait.py` attacks the claim that the marks are real, three ways:

- **Geometry** — every iris inside an eye socket, brows above the sockets, the
  mouth clear of the suture band. Caught the real bug where all 8 irises formed
  one straight row straddling both eyes.
- **Derivation** — a dead swarm renders differently from a living one; a revenue
  swarm renders a different mouth; entropy moves the brow. Caught the real bug
  where `render()` trusted a stale `dead_agents` list and could draw a living
  agent as dead.
- **Falsification** — an absent spine yields no agents and no smile; a torn
  final line does not discard the valid history.

## Files

| File | Purpose |
|---|---|
| `swarm_portrait.py` | Collector + renderer + headless-Chrome screenshot |
| `test_swarm_portrait.py` | The three-way self-test above |
| `swarm_portrait.html` | Generated, self-contained, offline |
| `swarm_portrait.png` | Generated portrait |
