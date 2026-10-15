# Digital Weather Station — local-first prototype

A mobile-friendly, offline-capable single-page dashboard for exploring network, information-diffusion, and human-attention measurements.

## Run

Open `index.html` in a modern browser. No build step, server, login, external library, or network connection is required. On Android, download/extract the bundle and open `index.html` in the browser. The **Load demo data** button fills the dashboard with synthetic signals to demonstrate functionality.

## Important limits

- Demo data are synthetic and are **not live telemetry**.
- The page does not connect to social networks, internet routers, solar-weather feeds, or other external services. Import measurements using CSV or connect a properly authorized collector separately.
- Imported data are processed in the browser and are not uploaded. The current build does not persist datasets between page reloads; export data if you need to retain them.
- Anomaly scores identify deviations from a series' median and median absolute deviation (MAD); they do not diagnose the cause.
- The lag scan aggregates observations into hourly buckets and reports exploratory Pearson correlations over lags of −12 to +12 hours. Its selected peak is subject to multiple-testing bias, confounding, missingness, and nonstationarity. It does not establish causation.
- Avoid importing personal identifiers or private user-level activity. Prefer aggregated, lawful, consent-respecting telemetry.

## CSV format

Required columns: `timestamp,metric,value`

Optional columns: `source,domain,event_id,note`

Example:

```csv
timestamp,metric,value,source,domain,event_id,note
2026-10-10T18:00:00Z,request_rate,123,example-monitor,network,,measured request rate
2026-10-10T18:00:00Z,latency_ms,87,example-monitor,network,,measured latency
```

Use ISO 8601 timestamps (UTC is recommended). One row represents one observation for one metric. For meaningful lag analysis, collect at a stable cadence and use aligned timestamps.

## Suggested deployment architecture for live data

1. Collect only from sources you are authorized to access (service health APIs, your own server logs, public aggregate feeds, and consented analytics).
2. Normalize timestamps to UTC and emit the CSV schema above.
3. Keep account IDs, tokens, IP addresses, and private messages out of the analysis dataset. Rotate/redact secrets in the collector.
4. Document metric units, collection cadence, source, missing-data behavior, and known confounders.
5. Validate candidate alerts against historical baselines and a holdout period before using them operationally.

## Bundle contents

- `index.html`: the working app
- `README.md`: usage and limitations
- `sample_observations.csv`: synthetic sample observations

## Hermes + OpenClaw integration

The bundle now includes a Python-standard-library JSON API, a CLI, and an Agent Skills-format `SKILL.md` for both Hermes and OpenClaw. The browser dashboard remains standalone; the API is the shared ingestion and evidence layer agents can use.

### Start the API

```bash
python3 dws_server.py
# default: http://127.0.0.1:8788
```

The API stores records under `~/.local/share/digital-weather-station/` as JSONL and appends SHA-256-linked records (`prev_hash` + `hash`) for tamper-evident sequencing. This is not a signed or externally anchored ledger; an administrator who can rewrite the files can rewrite the chain.

Endpoints:

- `GET /health`
- `GET /observations?limit=1000` (optional `&metric=...`)
- `POST /observations` with `{"observations":[...]}`
- `GET /analysis`
- `GET /events`
- `POST /events`

Set `DWS_API_TOKEN` to require bearer-token authentication. The service refuses a non-loopback bind without a token. If running the API on another host, set `DWS_HOST` to a private interface, set a strong token, and restrict access with the host firewall/Tailscale ACLs. Do not expose this API to the public internet. Keep tokens out of logs, skills, shell history, and prompts.

### CLI

```bash
bin/dws serve
bin/dws health
bin/dws import-csv sample_observations.csv
bin/dws analysis
bin/dws event "unexpected latency spike" "Source and time window" hypothesis
```

### Install agent skills

```bash
./install-agent-skills.sh
```

Defaults: OpenClaw `~/.openclaw/workspace/skills/digital-weather-station/SKILL.md`; Hermes `~/.hermes/skills/digital-weather-station/SKILL.md`. Override with `OPENCLAW_SKILLS_DIR` and `HERMES_SKILLS_DIR` if your installation uses different skill roots. Restart/reload each agent runtime if it does not discover the new skill automatically.

For a local agent on the same machine, use `DWS_URL=http://127.0.0.1:8788`. If the agent is containerized, its `127.0.0.1` is the container, not the host; use a reachable private/Tailscale host address and `DWS_API_TOKEN`. The skills provide operating instructions but do not themselves create network reachability or grant runtime tool permissions.

### Security and evidence boundaries

- API writes should be explicitly authorized by the operator. Agent skill instructions prohibit autonomous platform changes or unapproved collection.
- Import only authorized, aggregated observations. Do not collect private messages, credentials, personal identifiers, or individual-level behavioral traces.
- Anomaly flags are not evidence of malicious intent. Correlation and lag scans are not causal proof.
- The hash chain is tamper-evident only if its files and hashes are preserved independently; it is not a cryptographic signature or remote witness.

### Test

```bash
python3 -m unittest discover -s tests -v
```
