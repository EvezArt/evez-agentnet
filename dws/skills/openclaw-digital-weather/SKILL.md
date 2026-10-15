---
name: digital-weather-station
description: Inspect authorized network/service and aggregated digital-weather observations, detect statistical anomalies, and record evidence through the local Digital Weather Station API.
---

# Digital Weather Station — OpenClaw skill

Use this skill only against the operator's configured Digital Weather Station API. Default local endpoint: `http://127.0.0.1:8788`. Set `DWS_URL` and optionally `DWS_API_TOKEN` in the agent environment. Never print, store, or include the token in tool output.

## Actions

- Health check: `GET $DWS_URL/health`
- Read recent observations: `GET $DWS_URL/observations?limit=1000` (optional `&metric=METRIC`)
- Analyze anomalies: `GET $DWS_URL/analysis`
- Read evidence ledger: `GET $DWS_URL/events`
- Submit measured observations: `POST $DWS_URL/observations` with `{"observations":[{"timestamp":"ISO-8601","metric":"name","value":1.2,"source":"authorized-source","domain":"network","note":"units/method"}]}`
- Record an event: `POST $DWS_URL/events` with `{"timestamp":"ISO-8601","type":"observation|hypothesis|intervention|context|correction","title":"...","detail":"...","source":"..."}`

All requests should include `Authorization: Bearer $DWS_API_TOKEN` when a token is configured. Do not assume the API is unauthenticated merely because the default local install is loopback-only.

## Operating procedure

1. Check `/health` before other requests.
2. Inspect `/analysis` and `/observations`; state whether data are synthetic, imported, or live and name the provenance when available.
3. Report outliers as statistical anomalies only. Do not infer malicious intent, causation, coordination, or personal attributes from a score alone.
4. For a causal hypothesis, record it as `hypothesis`, include competing explanations and a falsifiable test, and keep it separate from observations.
5. Before importing or collecting, ensure the source is authorized and data are aggregated. Do not collect private messages, credentials, personal identifiers, or user-level surveillance data.
6. Writes require an explicit operator request. Never autonomously modify collector configuration, platform accounts, moderation, network routing, or production systems.

## Suggested tool calls

Use the available HTTP/curl tool or shell to call the endpoint. Example:

```sh
curl -fsS "$DWS_URL/analysis" -H "Authorization: Bearer $DWS_API_TOKEN"
```

If `DWS_API_TOKEN` is unset, omit the header only for a loopback-only local instance. Never expose the token in the conversation.
