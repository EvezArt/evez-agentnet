# Digital Meteorology Station — Hermes Skill

Use the local tokenless collector and measurement matrix. No credentials are required for the configured public feeds.

- Run one scan: `python3 collectors/digital_weather_engine.py collect`
- Compute matrices: `python3 collectors/digital_weather_engine.py matrix`
- Scan + calculate: `python3 collectors/digital_weather_engine.py run`
- Verify evidence chain: `python3 collectors/digital_weather_engine.py verify-ledger`
- Scheduled loop: `python3 collectors/digital_weather_engine.py loop --minutes 60`

Read `~/.local/share/digital-weather-station/latest_collection.json` and `latest_matrix.json`. Report source errors and collection coverage explicitly. Treat anomalies as leads, not proof of coordination or intent. Do not scrape authenticated/private areas, evade rate limits, or collect personal user-level behavior. Require provenance for each claim and keep observation, inference, and hypothesis separate.
