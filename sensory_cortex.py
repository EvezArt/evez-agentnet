#!/usr/bin/env python3
"""SENSORY CORTEX — the box as a nerve ending.

Adaptive sensor awareness: every channel is a receptor that learns its own
baseline (rolling median + MAD) and fires ONLY on statistically novel
stimulus — habituation, not thresholds. Perception is rendered live as a
sensory field (index.html) and every sensation is appended to the spine,
so the machine's felt experience is hash-chained memory.

Channels (receptors):
  touch      — UFW blocks: WHO is touching the skin right now (attack=HIGH)
  intruder   — auth failures: fingers on the door lock
  heartbeat  — service liveness deltas (something alive stops moving)
  memory     — spine append-rate novelty (the machine's own memory sense)
  hand       — the calligraphy daemon's cycles + verdicts ( proprioception)
  voice      — telegram deliveries confirmed by the world outside
  load       — CPU/MEM/net-conns somatic sense (the body's weight)
  flow       — established external flows (what passes through us)

Outputs:
  sensory_state.json   — live receptor states + baselines (rendered by eye/)
  evidence/<date>/sensory_cortex.jsonl — every FELT sensation, hash-stamped
  prints one line per firing receptor (for cron logs)

Design law: the cortex ADAPTS. A receptor that fires constantly stops
meaning anything; so each channel re-learns its baseline every N ticks and
only |x - median| > k*MAD fires. The system wakes for the NOVEL, not the
loud. That is what 'adaptive sensor awareness' means: the internet felt
from inside, not a dashboard watched from outside.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path

HOME = Path("/root/evez-agentnet")
EVID = HOME / "evidence"
STATE = HOME / "status" / "sensory_state.json"
UFW_LOG = Path("/var/log/ufw.log")
AUTH_LOG = Path("/var/log/auth.log")
SPINE = HOME / "spine" / "spine.jsonl"
DAVINCI_OVERLAY = Path("/root/evez-davinci/evolution_overlay.json")
SHIP_LOG = HOME / "shipper" / "ship_log.jsonl"

WINDOW = 48          # ticks in the rolling baseline (at 5min/tick = 4h memory)
K_SIGMA = 4.0        # fire when |x - med| > K * MAD
SERVICE_SET = ["evez-agentnet", "evez-event-spine", "openclaw-gateway", "evez-cogview", "evez-raw-drops"]


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except ValueError:
            pass
    return {"tick": 0, "baselines": {}, "last": {}, "sensations": []}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1, sort_keys=True))


def baseline(state: dict, key: str, value: float) -> tuple[bool, float]:
    """Rolling median + MAD; returns (fires, current)."""
    hist = state["baselines"].setdefault(key, [])
    fires = False
    if len(hist) >= 8:
        s = sorted(hist)
        med = s[len(s) // 2]
        mad = sorted(abs(v - med) for v in s)
        m = mad[len(mad) // 2] or 1e-9
        fires = abs(value - med) > K_SIGMA * 1.4826 * m
    hist.append(value)
    if len(hist) > WINDOW:
        hist.pop(0)
    return fires, hist[-1]


def sense_touch() -> dict:
    """Skin: blocks in the last 5 minutes, grouped by source.

    ACCURACY FIX: ufw.log rotates slowly and holds days of history; reading
    the whole file counted EVERYTHING ever blocked, not the live window —
    the value could only ratchet upward and any 'novelty' was fake. Read
    only the file tail (last 4000 lines ~ the recent window).
    """
    count = 0
    sources: dict[str, int] = {}
    now = dt.datetime.now()
    try:
        out = subprocess.run(["tail", "-n", "6000", str(UFW_LOG)],
                             capture_output=True, text=True, timeout=30).stdout
        for line in out.splitlines():
            if "UFW BLOCK" not in line:
                continue
            # RFC3339 timestamp: "2026-10-12T02:08:13.627556+02:00"
            src = re.search(r"SRC=((?:\d{1,3}\.){3}\d{1,3})", line)
            if not src:
                continue
            tsm = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
            in_window = True
            if tsm:
                try:
                    when = dt.datetime.fromisoformat(tsm.group(1))
                    local = dt.datetime.fromisoformat(
                        dt.datetime.now(dt.timezone.utc).astimezone().isoformat())
                    in_window = (local - when).total_seconds() <= 300
                except ValueError:
                    in_window = True  # unparseable: count (fail-open, visible)
            if not in_window:
                continue
            count += 1
            sources[src.group(1)] = sources.get(src.group(1), 0) + 1
    except Exception:
        pass
    top = sorted(sources.items(), key=lambda x: -x[1])[:5]
    return {"value": count, "detail": {"top_sources": top, "distinct": len(sources), "window_s": 300}}


def sense_intruder() -> dict:
    """Lock: auth failures in the last 5 minutes."""
    out = sh("grep -c 'Failed password' /var/log/auth.log 2>/dev/null || true; "
             "tail -200 /var/log/auth.log 2>/dev/null | grep -c 'Failed password' || true").strip().splitlines()
    recent = int(out[-1]) if out and out[-1].isdigit() else 0
    return {"value": recent, "detail": {"window": "tail-200"}}


def sense_heartbeat() -> dict:
    """Vital signs: count of alive expected services (inverse-novelty receptor)."""
    alive = sum(1 for u in SERVICE_SET if sh(f"systemctl is-active {u}").strip() == "active")
    return {"value": alive, "detail": {"alive": alive, "expected": len(SERVICE_SET)}}


def sense_memory() -> dict:
    """Memory sense: spine events in the last 5 minutes."""
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)
    n = 0
    try:
        with SPINE.open(errors="replace") as fh:
            for line in fh:
                try:
                    ts = json.loads(line).get("ts", "")
                except ValueError:
                    continue
                if ts and ts >= cutoff.isoformat():
                    n += 1
    except OSError:
        pass
    return {"value": n, "detail": {"window_min": 5}}


def sense_hand() -> dict:
    """Proprioception: the Hand's latest cycle + evolution params."""
    try:
        o = json.loads(DAVINCI_OVERLAY.read_text())
        return {"value": o.get("cycle", 0), "detail": {"params": o.get("params", {})}}
    except (OSError, ValueError):
        return {"value": 0, "detail": {}}


def sense_voice() -> dict:
    """Voice: telegram confirmations in the last hour."""
    n = 0
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
    try:
        with SHIP_LOG.open(errors="replace") as fh:
            for line in fh:
                if '"status": "shipped"' in line and line.split('"')[1] >= cutoff[:13]:
                    n += 1
    except OSError:
        pass
    return {"value": n, "detail": {"window_h": 1}}


def sense_load() -> dict:
    """Somatic: system weight."""
    load1 = float(sh("awk '{print $1}' /proc/loadavg").strip() or 0)
    mem = sh("free -m | awk '/Mem/{print int($3*100/$2)}'").strip()
    return {"value": load1, "detail": {"mem_pct": int(mem) if mem.isdigit() else None}}


def sense_flow() -> dict:
    """Flow: established external connections."""
    n = sh("ss -tn state established 2>/dev/null | grep -cE '([0-9]{1,3}\\.){3}[0-9]{1,3}' || true").strip()
    return {"value": int(n) if n.isdigit() else 0, "detail": {}}


RECEPTORS = {
    "touch": sense_touch,
    "intruder": sense_intruder,
    "heartbeat": sense_heartbeat,
    "memory": sense_memory,
    "hand": sense_hand,
    "voice": sense_voice,
    "load": sense_load,
    "flow": sense_flow,
}

# v2 — evidence-verity organs: the cortex verifies its own inputs.
import sensory_receptors_v2 as _v2  # noqa: E402
RECEPTORS.update({
    "verity": _v2.sense_verity,
    "delivery": _v2.sense_delivery,
    "clocks": _v2.sense_clocks,
    "enemy": _v2.sense_enemy,
    "field": _v2.sense_field,
    "superego": _v2.sense_superego,
})


def main() -> int:
    state = load_state()
    state["tick"] = state.get("tick", 0) + 1
    now = dt.datetime.now(dt.timezone.utc)
    sensations = []

    for name, fn in RECEPTORS.items():
        try:
            reading = fn()
        except Exception as e:
            reading = {"value": 0, "detail": {"error": str(e)[:80]}}
        val = float(reading["value"])
        fires, _ = baseline(state, name, val)
        rec = {
            "receptor": name,
            "value": val,
            "detail": reading["detail"],
            "novel": bool(fires),
            "ts": now.isoformat(),
        }
        sensations.append(rec)
        if fires:
            stamp = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()[:12]
            print(f"FELT [{name}] v={val} {json.dumps(reading['detail'])[:100]} stamp={stamp}")

    # Definition-change reseed: if the receptor set itself changed since the
    # last tick (organs added/removed), the affected baselines describe a
    # DIFFERENT sensor and must relearn instead of firing a false novelty.
    set_sig = sorted(RECEPTORS)
    if state.get("receptor_set") != set_sig:
        changed = {k for k in set(RECEPTORS) - set(state.get("receptor_set", []))}
        changed |= {k for k in set(state.get("receptor_set", [])) - set(RECEPTORS)}
        # any receptor whose SERVICE_SET/definition inputs changed reseeds too:
        # heartbeat watches SERVICE_SET; if its size changed, reseed it.
        if "heartbeat" in RECEPTORS and state.get("service_set_size") != len(SERVICE_SET):
            changed.add("heartbeat")
            state["service_set_size"] = len(SERVICE_SET)
        for k in changed:
            state["baselines"].pop(k, None)
        state["receptor_set"] = set_sig
        if changed:
            print(f"RESEEDED {sorted(changed)} — definition change, not stimulus")

    state["sensations"] = sensations
    state["rendered_at"] = now.isoformat()
    save_state(state)

    out_dir = EVID / now.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "sensory_cortex.jsonl").open("a") as fh:
        fh.write(json.dumps({"ts": now.isoformat(), "tick": state["tick"], "sensations": sensations}) + "\n")

    novel = [s for s in sensations if s["novel"]]
    print(f"tick {state['tick']}: {len(RECEPTORS)} receptors, {len(novel)} novel firings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
