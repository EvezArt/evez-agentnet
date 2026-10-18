# RuView disk bleed — rec_1792031285 — stopped and purged (2026-10-18, war-mode heartbeat tick)

Patrol finding that triggered this: `CORTEX-NOVEL superego v=76.0 re-measured=76 CONFIRMED {"disk_pct": 76}`

## What it was
- `ruview-demo` container writable layer: **80.8 GB**, all in ONE file:
  `/app/data/recordings/rec_1792031285.jsonl` — 80,407,892,081 B at first stat (01:14 mtime),
  80,844,908,933 B at final stat. Container had no bind mounts (`docker inspect .Mounts` = `[]`),
  so the file lived and grew inside the overlay layer.
- Live growth, measured twice this tick: **3,600,655 B / 12 s** and **4,605,280 B / 15 s**
  (≈300 KB/s ≈ **25–26 GB/day**). Free space was 47–48 GB ⇒ **under 2 days to disk-full**
  on the box that hosts the spine, evidence writes, docker and the whole war stack.
- Session span: dir created 2026-10-15 01:42 UTC, stopped 2026-10-18 01:47 UTC
  (API receipt `duration_secs: 256192` ≈ 71.2 h).
- Writer: **PID 1 (sensing-server) fd 17** — held open and appending even though the API
  reported the session `status:"completed"`, `frames:0` (bookkeeping lost count at zero).

## Proof the content was synthetic (no real sensing data lost)
- First frame of the file: `{"type":"sensing_update","timestamp":1792031284.937,"source":"esp32:offline",...}`
- Sparse probes at 5 GB, 20 GB, 40 GB, 60 GB, 75 GB offsets — every probe returned only
  `"source":"simulated"` / `"source":"esp32:offline"`. Zero `esp32` live frames.
- Pose joints all `confidence: 0.0`; `estimated_persons: 1` scaffold output.
- Watchdog evidence same day (evidence/2026-10-18/ruview_tailnet.jsonl): `source: esp32:offline`,
  UDP roundtrip ok — the real node was offline the whole session; CSI_SOURCE=auto fell back to simulation.

## What was done (all commands run this tick on the live box)
1. `POST /api/v1/recording/stop` (bearer from container env, never printed) →
   `{"duration_secs":256192,"recording_id":"rec_1792031285","success":true}`; file delta 12 s after = **0**.
2. Provenance samples pulled before deletion:
   - `ruview_rec1792031285_head.jsonl` (2 MB) sha256 `8779b8e172c19d4bff52f2018cfe0ddaf2aa63a64a0912bd9ac3ee6c3601fe14`
   - `ruview_rec1792031285_tail.jsonl` (20 MB) sha256 `fef104832f8d08bf4adfb319de20262e871cc47f17cd99b987af327ffd963fb7`
   both in this evidence directory.
3. `DELETE /api/v1/recording/rec_1792031285` → **silent no-op** (empty body, file persisted).
4. `rm` of the file inside the container → `/app/data` = 104K, no open fds on rec_ (`ls /proc/1/fd` clean).
5. Result: container layer 80.8 GB → **127 kB**; disk `/dev/sda1` 146G used 76% → **71G used 37%**, 123G free.
6. Post-state verified: `GET /api/v1/recording/list` → `{"recordings":[]}`; recordings dir empty;
   no auto-resume after 60 s; `/health` `{"status":"ok"}`; superego receptor re-reads `{'value': 37}`.

## Standing defect (not fixed tonight — compiled server)
- A "completed" recording session keeps appending via a held fd: stop must go through the API
  and even then the server's own DELETE is dead. If a recording is started again while the
  ESP32 node is offline (simulated source), the same 26 GB/day balloon recurs. Patch belongs
  upstream in sensing-server; until then the patrol's superego receptor is the tripwire.
- sensory cortex will flag the sudden 76→37 drop as novel for a render or two until the
  rolling baseline re-learns — habituation working as designed, not a fault.
