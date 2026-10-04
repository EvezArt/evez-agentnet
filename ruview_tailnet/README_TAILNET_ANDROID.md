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

## Provisioning the ESP32 (server side)

`provision_node.sh` does everything that does not need the board in hand, so
the only manual step left is plugging it in:

    ./provision_node.sh --ssid "HomeWifi" --pass "hunter2" --agg 192.168.1.50
    ./provision_node.sh --ssid "HomeWifi" --pass "hunter2" --agg 192.168.1.50 --16mb --build

- `--agg` is the phone's LAN IP on the sensing WiFi.
- `--4mb` / `--16mb` select the flash layout; `--build` rebuilds in
  `espressif/idf:v5.4` (required when the build does not yet match).
- It refuses to flash if the built image does not match the requested size,
  and asserts `IDF_TARGET`, `BOOTLOADER_APP_ROLLBACK_ENABLE` and
  `ESP_WIFI_CSI_ENABLED` before writing.
- Site credentials go to `firmware/esp32-csi-node/sdkconfig.defaults.site`,
  mode 600 and gitignored. Never commit that file.

Both flash sizes are verified building: 4MB -> `partitions_4mb.csv`, 16MB ->
`partitions_16mb.csv`, each with `ROLLBACK_ENABLE=y`.

**Upstream overlay-order defect (found here, fixed in the provisioner):**
`sdkconfig.defaults.16mb` states it layers on top of
`sdkconfig.defaults.esp32c6`, but the firmware RUNBOOK's documented `cat` order
puts `16mb` first. Last file wins in an sdkconfig overlay, so esp32c6's 4MB
layout overwrites the 16MB request and the build silently produces a 4MB
image — while the same RUNBOOK's verification table demands
`FLASHSIZE="16MB"`. Anyone following the RUNBOOK verbatim gets a wrong-sized
image and may not notice. The provisioner concatenates in dependency order:
`sdkconfig.defaults sdkconfig.defaults.esp32c6 [sdkconfig.defaults.16mb]`.

Flash offsets come from the build's own `flash_args`, never hand-copied. Both
the 4MB and 16MB tables currently place the app at `0x20000`, but the
`--flash_size` in those args is board-specific and a partition-table change
upstream must not be able to silently flash the wrong layout.

## What is deliberately NOT done

Public UDP 5005 is not opened. The CSI data plane has no message
authentication (ADR-296 step two — per-device keys and replay rejection — has
not landed), so exposing it to the internet would let anyone inject valid-shaped
frames and drive presence/vital outputs. The node reaches the tailnet, not the
reverse.

## Eliminating the phone: not possible on ESP32-C6

Researched 2026-10-04. There is **no `esp-tailscale`** — `tailscale/esp-tailscale`
is a 404, has never existed per the Wayback Machine, and is absent from the
Tailscale org. No official Tailscale Embedded SDK or MCU port exists;
Tailscale's IoT positioning is Linux agents on SBCs.

Third-party option: **MicroLink** (https://github.com/CamM2325/microlink, ESP-IDF
component, not affiliated with Tailscale). Do not adopt it for this node:

- Not confirmed for ESP32-C6 specifically.
- Reproducible crashes under sustained tunnel traffic, hardware-confirmed:
  issue #17 (`pbuf_free: p->ref > 0` assert + reboot), issue #20 (a ~600 KB TCP
  proxy rebooted an S3 N16R8 mid-transfer on IDF v5.3, clean only after a fix),
  issue #28 (six lwIP thread-safety violations found via
  `CONFIG_LWIP_CHECK_THREAD_SAFETY`, including `netif_set_up()`/`udp_new()`
  called off-thread).
- It needs a custom lwIP netif (WireGuard MTU 1420), so plain `sendto()` to a
  100.x address is not guaranteed transparent — the CSI sender would have to be
  reworked and re-validated against the ADR-018 frame path.
- CSI capture already saturates the radio's TX airtime and consumes the WiFi
  buffer pools (see the sdkconfig comments about `sendto ENOMEM` at 10/s). Adding
  a WireGuard tunnel on top competes for the same constrained resources.

**Decision: keep the phone relay.** It is a byte-forwarder, has no crypto
budget, and is already proven end to end. Revisit only if a C6-supported,
stability-demonstrated tunnel exists.

## MicroLink / Tailscale-direct on the ESP32 — researched and rejected

A dedicated research pass (2026-10-04) reached a different conclusion than a
naive reading would: Tailscale-direct is not viable on this node, and its
recommended alternative (open public UDP 5005) is rejected here on security
grounds. Both halves recorded so the question does not get re-litigated.

### No official option exists

`github.com/tailscale/esp-tailscale` is a 404, has no Wayback snapshot, and is
absent from the Tailscale org. No MCU/embedded SDK exists — Tailscale's IoT
story is Linux agents on SBCs.

### MicroLink is not safe to put on a CSI node

https://github.com/CamM2325/microlink (third-party, unaffiliated). Precise
findings worth keeping:

- **C6 is explicitly untested upstream** ("Should Work (Untested)"). A
  community fork proves C6 builds/runs, not the CSI + 128-TX-buffer
  combination.
- **Plain `sendto()` is not supported.** MicroLink builds a real lwIP netif
  with a /10 netmask *prepended* to `netif_list`, so lwIP's linear netmask scan
  would route a `100.x` destination out the tunnel — but the library itself
  calls `udp_bind_netif()` and binds to the VPN IP, i.e. the authors did not
  trust routing. Treat it as unverified.
- **Receive path is a documented crash.** `wireguardif.c` calls `ip_input()`
  directly from the WireGuard task instead of `netif->input`. Issues #17
  (`pbuf_free: p->ref > 0` assert + reboot), #20 (~600 KB TCP proxy rebooted an
  S3 N16R8 mid-transfer on IDF v5.3), #28 (six lwIP thread-safety violations,
  incl. `netif_set_up()`/`udp_new()` off-thread).
- **MTU mismatch:** netif MTU 1420 but Tailscale's tunnel MTU is 1280 — inbound
  breaks (issue #34, open).
- **Port conflict:** grabs UDP 51820 (issue #5).
- **`microlink_send()` is a stub** — `/* TODO: Route through WireGuard tunnel */`,
  falls back to DERP queueing.
- RAM: 116 KB static SRAM / 950 KB flash, but 1 MB of buffers wants PSRAM. C6
  has **512 KB SRAM and no PSRAM** on most modules, so buffers must drop to
  64 KB — and issue #35 documents that sub-64 KB configs were *silently broken*
  by an unsigned underflow that made the control plane return GOAWAY.

Also rejected: `esphome-tailscale` (PSRAM is a hard requirement — rules out C6),
`0xdilo/tailscale-esp32` (S3 only), WARP (no client at that resource level).

### Why public UDP 5005 is also rejected

The research recommends pointing the ESP32 at `80.241.209.34:5005` — no hole
punching needed, plain `sendto()` unmodified, no lwIP risk. Mechanically
correct, and it is the simplest option available.

It is not acceptable here. That data plane has **no message authentication**:
ADR-296 step two (per-device keys, MAC/AEAD, monotonic sequence numbers,
freshness window, replay rejection) has not landed. The ADR-296 allowlist only
restricts *which addresses* may send — an IP allowlist is not authentication.
An open port therefore lets anyone on the internet inject valid-shaped ADR-018
frames and drive presence, breathing, fall-detection and automation outputs.
Source-spoofing a residential IP is trivial, and NAT hairpin/amplification
makes it worse.

The phone relay stays: it is a byte-forwarder with no crypto budget, needs no
infrastructure, and is already proven end to end. Revisit only when ADR-296
step two lands — at that point public UDP becomes defensible and the phone
leaves the data path entirely.
