# EVEZ RuView + Hermes Repair Runbook

Purpose: diagnose the existing RuView Tailscale sensing endpoint and Hermes/OpenClaw operator surfaces without disabling authentication or exposing services publicly.

## Important known state
- RuView host documented as Tailscale IP 100.126.180.47; public URL previously provided by operator: https://vmi3544756.mooneye-shade.ts.net/
- RuView HTTP API/UI: TCP 3000; sensing WebSocket: TCP 3001; CSI data-plane UDP 5005.
- The mobile relay belongs on the Galaxy A16 / Termux, forwarding ESP32 CSI frames from the same Wi-Fi LAN to the RuView Tailscale IP.
- No physical ESP32 CSI sensor was present in the latest repository onboarding note dated 2026-10-04. Without it the server can correctly report simulated or esp32:offline; software alone cannot make the sensing hardware live.
- EVEZ mobile relay documented on Linux localhost:8788; NextClaw:8787; OpenClaw Gateway:18789; Hermes URL is configured and not guaranteed to be localhost:18790.

## Step 1: Test the endpoint from the phone
In Termux (the Tailscale Android app must already be signed in):
```bash
curl -sS -i --max-time 8 https://vmi3544756.mooneye-shade.ts.net/health
curl -sS -i --max-time 8 https://vmi3544756.mooneye-shade.ts.net/api/v1/nodes
```
Interpretation:
- 200 with JSON means the HTTPS endpoint routes to a healthy API.
- 502 means the HTTPS proxy has no healthy upstream or the upstream refused/failed.
- 401 means routing works but the endpoint requires credentials.
- DNS/TLS/timeout failures mean investigate Tailscale Serve, tailnet connectivity, hostname configuration, or certificate/routing.

## Step 2: Safe checks on the Linux host
Run these on the host that serves the endpoint; these are read-only diagnostics:
```bash
tailscale status
tailscale serve status
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
ss -ltnup | grep -E ':(3000|3001|5005|8787|8788|18789|18790)\\b' || true
docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' ruview-demo 2>/dev/null || true
curl -sS -i --max-time 4 http://127.0.0.1:3000/health
curl -sS -i --max-time 4 http://127.0.0.1:8788/health
curl -sS -i --max-time 4 http://127.0.0.1:18789/ || true
```
Do not print environment variables, tokens, or full container config. Do not switch to Funnel/public binds.

## Step 3: Restart only after collecting evidence
If `ruview-demo` is stopped, inspect its logs with:
```bash
docker logs --tail 120 ruview-demo
```
If its deployment is Compose-managed, change into the actual RuView deployment directory, inspect `docker compose ps`, then use `docker compose up -d` only if the configured service is safe to start. Do not guess the compose directory or redeploy from an unrelated checkout.
Inspect Tailscale Serve status before altering its config. Keep RuView private to the tailnet and preserve authentication.

## Step 4: Validate actual sensing
From the phone, read `/health` and `/api/v1/nodes`. A successful UDP send alone does not prove delivery. Do not use `--inject-probe` for routine checks because it can register a phantom node and make health look live. Real CSI requires a compatible ESP32-S3/C6 node running the repository firmware and targeting the phone's Wi-Fi LAN IP on UDP 5005.

## Step 5: Hermes and OpenClaw
Do not assume Hermes listens on 18790; use the configured operator URL in the private EVEZ config. On the Linux host, inspect running process/service names and local listening ports without printing secrets:
```bash
systemctl --user --no-pager --type=service --all | grep -Ei 'hermes|openclaw|nextclaw|evez|ruview' || true
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```
For OpenClaw, keep Gateway authentication enabled. For the relay, do not expose /v1/mission without an authentication gate. Confirm Relay digest validation before relying on evidence-chain claims.

## What to send back
Paste the status code and sanitized response from Step 1, plus output from Steps 2 checks. Redact bearer tokens, cookies, private keys, Wi-Fi passwords, and any credential material.
