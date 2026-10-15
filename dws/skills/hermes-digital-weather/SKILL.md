---
name: digital-weather-station
description: Use the Digital Weather Station local API to inspect observations, review robust anomaly summaries, and record evidence without confusing correlation with causation.
---

# Digital Weather Station — Hermes investigator/verifier

Default endpoint: `http://127.0.0.1:8788`. Configure `DWS_URL`; configure `DWS_API_TOKEN` if API authentication is enabled. Treat the station as an evidence source, not an oracle.

## Read operations

- `GET /health`: verify service and authentication status.
- `GET /observations?limit=1000`: retrieve recent observations; filter with `&metric=...`.
- `GET /analysis`: robust median/MAD outlier summary.
- `GET /events`: read hash-chained event records.

## Write operations (only when explicitly requested)

- `POST /observations`: body `{"observations":[{"timestamp":"ISO-8601","metric":"metric_name","value":1.0,"source":"authorized-source","domain":"network","event_id":"","note":"unit and collection method"}]}`.
- `POST /events`: body `{"timestamp":"ISO-8601","type":"observation|hypothesis|intervention|context|correction","title":"short title","detail":"evidence, source, uncertainty, test","source":"agent"}`.

Include `Authorization: Bearer $DWS_API_TOKEN` when configured. Never reveal credentials.

## Verification protocol

1. Confirm service health, data count, time range, source, and whether data are synthetic or measured.
2. Check timestamp normalization, units, sample cadence, missingness, and baseline size before interpreting scores.
3. Treat robust z-score flags as anomaly candidates, not proof of cause or intent.
4. Treat lagged correlation as exploratory; examine confounders, seasonality, multiple-testing bias, and out-of-sample replication before making causal claims.
5. Separate `observation`, `hypothesis`, `intervention`, `context`, and `correction` records. Record source references and uncertainty.
6. Do not infer an individual's mental state, identity, intent, or wrongdoing from aggregate metrics. Do not collect private messages, credentials, or identifying behavioral traces.
7. Do not execute external actions, change platform settings, or launch collectors without explicit authorization. The intended workflow is: observe → investigate → verify → authorize → execute → record.

Use HTTP/curl or the agent's available HTTP tool. Keep outputs concise, include provenance, and say when evidence is insufficient.
