# EVEZ EYE

Operations console for a single operator. Palantir's ontology idea, pointed at
one person's stack instead of an organisation's data lake.

Live now at **http://127.0.0.1:8900/** (loopback only).

## Files

| File | Purpose |
|---|---|
| `collect.py` | Probes the stack into `data.json`. Nothing is asserted or cached |
| `render.py` | Turns `data.json` into a single self-contained `index.html` |
| `serve.py` | Refresh daemon: re-collects every N seconds and serves the result |
| `data.json` | Latest snapshot |
| `index.html` | Generated page |

## Sibling: the swarm selfie

The EYE shows an operator their stack. `../SWARM_SELFIE.md` covers the other
direction — a portrait of the swarm looking at itself, generated from spine and
EYE telemetry by `../swarm_portrait.py`.

## Run

```bash
python3 collect.py && python3 render.py   # one-shot snapshot
python3 serve.py --port 8900 --interval 60 # live console
```

## Safety properties (deliberate, and worth keeping)

- **Loopback only.** `serve.py` binds `127.0.0.1`, never `0.0.0.0`. An ops
  console is not a public service.
- **No egress.** The daemon makes no outbound requests. Operator stack
  telemetry has no business leaving the machine, and a monitoring agent that
  phones home is the same bug class as the credential leak this repo cleaned up.
- **Strict allowlist.** Only `index.html` and `data.json` are servable.
  `../../etc/passwd` returns 404.
- **CSP with `connect-src 'none'`** so a future edit to `index.html` cannot
  introduce an outbound request. Plus `nosniff`, `no-referrer`, `no-store`.

## The distinction that matters

A port **bound** to `0.0.0.0` is not a port **reachable** from the internet.
ufw INPUT policy is DROP, so a public bind with no ACCEPT rule is firewalled.
The EYE classifies every listener as `EXPOSED` (reachable), `GUARD` (public
bind, firewalled), tailnet, or loopback — and only `EXPOSED` counts as a
finding. A console that cries wolf on every public bind is one you learn to
ignore.

Same principle in credential scanning: this repo's own detector code and its
test fixtures both contain the literal prefix `clh_`, so a naive prefix grep
reports a live credential where only a test string exists. `collect.py` requires
a full-length literal and excludes `TESTONLY`/`REDACTED` markers. The EYE
currently reports **0 live credentials**; `stack_health.py` reports one, and it
is wrong.
