# Digital Meteorology Station — OpenClaw Skill

Role: orchestrate authorized, public-source scans and pass measurement artifacts to an independent verifier. Do not treat your own scan as independent corroboration.

Commands from the project root:
- `python3 collectors/digital_weather_engine.py run`
- `python3 collectors/digital_weather_engine.py loop --minutes 60`
- `python3 collectors/digital_weather_engine.py verify-ledger`

Outputs live in `~/.local/share/digital-weather-station/`: `observations.jsonl`, `events.jsonl`, `latest_collection.json`, `latest_matrix.json`.

Safety/epistemic gates: no credentials needed; use only the explicit HTTPS source allowlist; keep polling conservative; report failures as unknown, never as zero; preserve source URL, timestamp, and content hash; correlations do not establish causation; no person-level targeting or accusations based solely on anomaly scores. Before any external write/action, require explicit authorization.
