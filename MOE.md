# EVEZ MoE — mixture of experts

Routing across the six models actually installed on this host, cheapest
adequate expert first.

## The idea

A mixture-of-experts isn't interesting as a diagram. It's interesting because
it lets a task use a 0.6B model when that's enough, and escalate to 3.2B only
when it isn't. The saving is real and measurable.

```
nomic-embed-text:latest   137M     262MB   EMBED ONLY
qwen3:0.6b              751.63M     498MB   generative
deepseek-r1:1.5b           1.8B    1066MB   generative
qwen3:1.7b                 2.0B    1296MB   generative
hermes3:3b                  3.2B    1926MB   generative
hermes3:3b-fast             3.2B    1926MB   generative
```

## Two-tier gate

**Tier 1 — deterministic (default).** Task shape is inferred from keyword cues
(`code`, `classify`, `summarise`, `extract`, `reason`) and routed to the
cheapest expert in that kind's preference list. Zero latency, zero cost, always
available.

| Task kind | Preference (cheapest first) |
|---|---|
| `classify` | qwen3:0.6b → hermes3:3b-fast → hermes3:3b |
| `extract` | qwen3:0.6b → hermes3:3b-fast |
| `summarise` | qwen3:1.7b → hermes3:3b-fast → hermes3:3b |
| `reason` | deepseek-r1:1.5b → qwen3:1.7b → hermes3:3b |
| `code` | qwen3:1.7b → hermes3:3b → deepseek-r1:1.5b |

**Tier 2 — Jev gate (optional).** With `TYPESAFE_API_KEY` set, Jev evaluates
which installed expert suits the task and returns a probability distribution
plus confidence. Used only when confidence clears `JEV_MIN_CONFIDENCE` (0.55);
otherwise it abstains and the deterministic tier decides. The abstention reason
is carried into the route log.

## Usage

```bash
python3 moe_cli.py roster                          # what's really installed
python3 moe_cli.py route "classify this ticket"    # which expert, and why
python3 moe_cli.py cost "..." --kind classify      # cost + escalation path
python3 moe_cli.py ask "..." --kind summarise      # route + generate
python3 moe_cli.py routes                          # routing history
```

## Measured

Real generation through the router, on this host:

| Task | Expert | Elapsed | Tokens |
|---|---|---|---|
| `Reply with exactly: ROUTER_OK` (classify) | qwen3:0.6b | **0.99s** | 5 |
| `classify the urgency of a payment outage` (classify) | qwen3:0.6b | **1.9s** | — |
| `what does a hash chain provide?` (summarise) | qwen3:1.7b | 39.6s | — |

Classification at 0.99s on a 498MB model versus ~40s on 1296MB is the entire
point: the cheap expert is ~20× faster for the task it is actually qualified
for.

## Two real bugs the tests caught

**1. Silent empty answers from reasoning models.** `qwen3` and `deepseek-r1`
emit a separate `thinking` field and spend `num_predict` on chain-of-thought
*before* producing any answer. With `num_predict=400` the model thought until it
hit the limit and returned `response: ""` — HTTP 200, `done_reason: "length"`,
no text. Without a guard that reads as success.

Fixed: send `think: false`, raise the budget for reasoning families, and treat
an empty response as `ok: False` with `thinking_chars` reported.

**2. Embed-only model routed to generation.** `nomic-embed-text` produces
vectors, not text — it cannot answer a prompt. The initial preference list
included it. Fixed: generative routing filters any embed-only model, and
embedding has its own code path (`moe_infer.embed`).

Also caught: no `classify` keyword cues existed, so classification silently fell
through to `summarise` and never used the cheapest model. That is the exact
failure a MoE exists to avoid.

## Honesty constraints

Consistent with the rest of this repo:

- **The roster is verified, not aspirational.** `installed_experts()` queries
  Ollama. A model that isn't there is never routed to.
- **No experts means failure, not a default.** If Ollama is unreachable the
  router returns `expert: None, gate: "none"`. It does not quietly return the
  biggest model as if routing had succeeded.
- **Every route is logged** with gate, reason, and confidence — a bad route is
  visible rather than invisible.
- **Empty model output is a failure**, not a successful empty string.

## Files

| File | Purpose |
|---|---|
| `moe_router.py` | roster discovery, task classification, two-tier gate |
| `moe_infer.py` | generation + separate embedding path |
| `moe_cli.py` | command line |
| `test_moe_router.py` | 31 assertions incl. no-invented-expert |
| `test_moe_infer.py` | 13 assertions incl. the thinking-budget regression |
| `moe/routing.jsonl` | every route, with reason and confidence |

## Verification

```bash
python3 test_moe_router.py   # 31/31
python3 test_moe_infer.py    # 13/13, includes live inference
```
