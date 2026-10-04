# RuView over Tailscale, onto the Android phone

Status 2026-10-04: the tailnet path is live and attested. The remaining
physical step is the ESP32 radio.

## What is actually connected

    ESP32 CSI node
        |  UDP 5005, phone's LAN IP (phone shares the WiFi the node is on)
        v
    Android phone (Termux relay, ruview_relay.py)
        |  UDP 5005 over Tailscale
        v
    vmi3544756 100.126.180.47:5005  -> ruview-demo
        |  HTTP/WS 3000 (/health, /api/v1/*, /ws/sensing)
        v
    phone browser / Termux client

Why the phone is in the middle: an ESP32 on a home WiFi has no route to the
tailnet, and an Android phone cannot read CSI from its own WiFi. So the node
sends to the phone, and the phone forwards the bytes. The relay never parses,
rewrites, or synthesises a frame - whatever the node emits arrives at the
server byte-for-byte.

## Server side (already done, on this host)

`/root/ruview/docker-compose.yaml` publishes three ports, each bound to the
Tailscale address 100.126.180.47 and never 0.0.0.0:

| Port | Purpose |
|---|---|
| 3000/tcp | HTTP API, UI, and `/ws/sensing` |
| 3001/tcp | dedicated sensing WebSocket |
| 5005/udp | CSI data plane (ESP32 / phone relay) |

The UDP receiver defaults to loopback (ADR-296) and refuses a routable bind
with no allowlist. The allowlist is what makes this safe to open:

    RUVIEW_UDP_BIND=0.0.0.0
    RUVIEW_UDP_ALLOW=100.64.0.0/10     # Tailscale CGNAT range, nothing else

Verified:
- Frame over UDP 5005 flipped `/health` source `simulated` -> `esp32`
- Bridge-sourced frames (172.17/16, not allowlisted) were dropped, node never
  appeared in `/api/v1/nodes`
- Public interface refuses 3000/3001 (`Connection refused`)
- `/ws/sensing` 401 without a bearer token, 101 with one, and via a
  `POST /api/v1/ws-ticket` single-use ticket for browser clients
- Host-header validation still rejects `Host: evil.example.com` with 421

## Phone side (run once, from Termux)

    bash ruview_install.sh

It installs python, drops the relay at `~/ruview/ruview_relay.py`, and runs
`--status` to prove reachability.

**It does not install Tailscale in Termux, and must not.** Android allows one
VPN app to hold the VPN slot; the Tailscale Android app already owns it and the
phone is already on the tailnet (`100.78.25.90`, hostname EVEZ, online). A
Termux tailscale would fail to bind. The tailnet IP the phone needs is simply
the one the app already holds. If that app is ever signed out, sign it back in
from its own UI — no auth key required for a device that is already enrolled.

Then:

    ip -4 addr show wlan0                      # note the phone's LAN IP
    ~/ruview/start-relay.sh                    # forwards LAN CSI -> tailnet
    python ~/ruview/ruview_relay.py --status   # confirm the server sees it

The ESP32's `CONFIG_CSI_TARGET_ADDR` is set to the phone's **LAN IP on the
sensing WiFi** (not the Tailscale IP, not the VPS address) and
`CONFIG_CSI_TARGET_PORT=5005`.

## Honesty note on `--status`

A UDP send proves only that the local stack emitted a datagram; UDP cannot
confirm receipt. `--status` therefore reports the server's own view
(`/health`, `/api/v1/nodes`) rather than claiming delivery from a local send.
`--inject-probe` sends a real frame to force proof of receipt, but it flips
`/health` to `esp32` and registers a probe node, so it is diagnostic-only and
never the default.

## Watchdog

`ruview-tailnet-watch.service` probes the whole path every 15 minutes: container
up, health answering, and a real frame round-tripped through UDP 5005 and
confirmed server-side in `/api/v1/nodes`. It appends one JSON line per probe to
`evez-agentnet/evidence/<UTC-date>/ruview_tailnet.jsonl` and logs to
`/root/ruview/tailnet_watch.log`. A liveness attestation, not an accuracy claim.

## One-paste phone setup

There is no adb, no ssh, and no Termux-ssh on the phone, so nothing can be
installed onto it from here. The phone therefore pulls its own installer over
the tailnet and reports its LAN address back.

`ruview-bootstrap.service` (port 8099 on 100.126.180.47, bearer-gated) serves
three files and accepts one POST. In Termux on the phone, one command:

    bash -c "$(curl -fsSL http://100.126.180.47:8099/bootstrap.sh)"

It checks the tailnet path, installs the relay to `~/ruview/`, parses it before
trusting it, reports the phone's `wlan0` LAN IP to `/register`, starts the
relay detached with a wake lock, and verifies.

**Why the phone registers its own LAN address.** That IP is what the ESP32 must
target, and it is a private RFC1918 address on a network the VPS cannot see.
Having the phone self-report means the ESP32 target is never a value someone
reads off a screen and retypes. `provision_node.sh` reads the registry
automatically:

    ./provision_node.sh --ssid "HomeWifi" --pass "..." --agg-registered

`--agg-registered` refuses to fall back to the VPS address when no phone has
registered, because flashing a node pointed at the wrong aggregator is a
failure that only shows up as silent `esp32:offline` later.

Registration is advisory. It records an operator hint; it never changes a
firewall rule or redirects anything by itself. The endpoint accepts only
private IPv4 and rejects anything else.
