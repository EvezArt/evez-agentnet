# RUVIEW SENSOR ONBOARDING — going from simulated to real
*What is already true, and the only thing standing between RuView and real presence sensing.*

## Current state (verified 2026-10-04)
- Container `ruview-demo` bound Tailscale-only on 3000/tcp, 3001/tcp, 5005/udp
  (all on 100.126.180.47; public interface refuses them)
- UDP 5005 data plane is ROUTABLE with source allowlist 100.64.0.0/10;
  bridge-sourced frames verified dropped
- `/health` source has been observed flipping `simulated` -> `esp32` on a real
  frame delivered over the tailnet. With no node attached it reads
  `esp32:offline` — still no live radio, but the path is proven, not claimed
- Phone-side relay exists and was exercised end to end:
  /root/ruview/android/{ruview_relay.py,ruview_install.sh}
- Watchdog `ruview-tailnet-watch.service` attests the path every 15 min into
  evidence/<date>/ruview_tailnet.jsonl
- Full procedure: /root/ruview/README_TAILNET_ANDROID.md
- `SENSING_ALLOWED_HOSTS` already whitelists the tailnet address and `vmi3544756.tail613e80.ts.net:3000`
- Firmware source is in the repo: firmware/esp32-csi-node (ESP32-S3 / C6, ESP-IDF v5.4)

## The single blocker
No CSI sensor node exists. Not offline — nonexistent on this host: no USB serial device,
no ESP-IDF toolchain installed, zero clients ever paired. WiFi sensing needs a physical
ESP32 on the same WiFi as the space to sense. There is no software workaround; the radio
has to be there.

## Bring it real
1. Plug an ESP32-S3 (or C6) into the machine — it appears as /dev/ttyUSB0 or /dev/ttyACM0
2. Flash firmware/esp32-csi-node (ESP-IDF v5.4; see firmware RUNBOOK.md + docs/build-guide.md)
3. Give the node the WiFi SSID/password of the network covering the space
4. Point it at the sensing server over the tailnet: 100.126.180.47:3000
5. Watch it flip: `/health` source stops being "simulated" and clients >= 1

## Once a node is live
codex_watch.py now probes /health every 15 minutes and records the sensing source, so the
transition from simulated to live is attested in evidence/<date>/codex_watch.jsonl instead of
being a claim. Presence, breathing and departure events then become measurements, not guesses.
