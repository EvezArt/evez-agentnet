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

## Tokenless autonomous collector (new)

`collectors/digital_weather_engine.py` uses only Python's standard library and polls an explicit HTTPS allowlist of anonymous public feeds: NOAA SWPC alerts, USGS earthquake GeoJSON, NASA EONET events, CISA cyber advisories, and GitHub Status RSS. No API keys or manually provided tokens are used. A source that fails is marked `error`/unknown rather than interpreted as zero events.

From the project root:

```bash
python3 collectors/digital_weather_engine.py collect
python3 collectors/digital_weather_engine.py matrix
python3 collectors/digital_weather_engine.py run
python3 collectors/digital_weather_engine.py loop --minutes 60
./start-autopilot.sh
python3 collectors/digital_weather_engine.py verify-ledger
python3 tests_tokenless.py
```

Outputs default to `~/.local/share/digital-weather-station/` (override with `DWS_DATA_DIR`). `observations.jsonl` and `events.jsonl` are append-only hash-chained records; `latest_collection.json` records coverage/errors; `latest_matrix.json` reports robust-MAD anomaly flags and exact-timestamp pairwise Pearson correlations. Correlations are exploratory, and feed item counts measure feed publications—not total internet attention or human intent.

Hermes and OpenClaw instructions are in `skills/hermes/SKILL.md` and `skills/openclaw/SKILL.md`. Run `./install-agent-skills.sh` to copy them into the default local skill directories (override with `HERMES_SKILLS_DIR` and `OPENCLAW_SKILLS_DIR`). Run `./start-autopilot.sh` to start the hourly collector in the background; stop it with `kill $(cat ~/.local/share/digital-weather-station/collector.pid)`. A GitHub Actions workflow performs a six-hourly public-source scan without repository secrets and stores short-retention artifacts. Hosted CI artifacts are not a permanent ledger; copy/export them to a durable store if long-term retention is required. For always-on collection, run the loop on your own trusted machine or server.

The collector is intentionally conservative: it does not crawl arbitrary sites, access private accounts, bypass login/rate limits, track individuals, or infer wrongdoing from statistical anomalies. Expand the allowlist only after checking source terms, cadence, data schema, and provenance requirements.
