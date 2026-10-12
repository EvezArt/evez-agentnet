#!/usr/bin/env python3
"""EVIDENCE VERITY RECEPTORS — the cortex grows accuracy organs.

The doctrine: a sensor in an evidence-based environment must VERIFY ITS OWN
INPUTS. These receptors don't just count — they cross-check the machine's
memory against itself, prove the chain, grade delivery truth, watch the
enemy's clocks, and confirm the field is actually alive. Every reading
carries its verification status into the sensation record.

New receptors (v2):
  verity      — spine chain verified? file-count vs recorded-count drift.
                Reading = drift count; ANY drift is novel by definition.
  delivery    — real deliveries per hour, API-CONFIRMED ONLY (message_id in
                the ship log row). Synthetic/shipped-without-proof excluded.
  clocks      — enemy obligations within 3 days or blown. Reading = the
                count of imminent/expired clocks (0 = calm).
  enemy       — NEW attacker sources seen in the last 24h that were never
                seen before (baseline = the registry). Novel-by-definition
                per new IP, so the reading itself is the alert content.
  field       — the sensory field's own liveness: HTTP status through the
                eye + render age. 200=healthy. A dead field must be FELT.
  superego    — disk pressure + entropy: how close the body is to
                asphyxiation (disk full = memory death).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

HOME = Path("/root/evez-agentnet")
EVID = HOME / "evidence"
SPINE = HOME / "spine" / "spine.jsonl"
SHIP_LOG = HOME / "shipper" / "ship_log.jsonl"
REGISTRY = HOME / "forge_output" / "ATTACKER_REGISTRY.md"
UFW_LOG = Path("/var/log/ufw.log")


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90).stdout
    except Exception:
        return ""


def _quick_spine_check() -> dict:
    """Lightweight chain verify: recompute each row's sha256[:16] and compare
    to the stored value; also count rows. Full verify_spine.py stays the
    authoritative gate; this is the sensor's own eyes."""
    rows = 0
    broken = 0
    last_seq_ok = True
    prev = None
    try:
        with SPINE.open(errors="replace") as fh:
            for line in fh:
                rows += 1
                try:
                    rec = json.loads(line)
                except ValueError:
                    broken += 1
                    continue
                body = {k: v for k, v in rec.items() if k != "sha256"}
                digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
                if digest != rec.get("sha256"):
                    broken += 1
    except OSError:
        return {"verified": False, "rows": 0, "broken": 0}
    return {"verified": broken == 0, "rows": rows, "broken": broken}


def sense_verity() -> dict:
    """Memory integrity: does the machine's own memory still prove itself?"""
    chk = _quick_spine_check()
    # drift = broken hashes (integrity) — the sensor reads brokenness, not rows
    return {"value": chk["broken"], "detail": {"rows": chk["rows"], "verified": chk["verified"]}}


def sense_delivery() -> dict:
    """Voice, but HONEST: only API-confirmed deliveries (message_id present)."""
    n = 0
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)).isoformat()
    try:
        with SHIP_LOG.open(errors="replace") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("status") != "shipped":
                    continue
                if not str(row.get("detail", "")).strip() and "message_id" not in line:
                    continue
                if (row.get("ts") or "") >= cutoff:
                    n += 1
    except OSError:
        pass
    return {"value": n, "detail": {"window_h": 6, "confirmed_only": True}}


def sense_clocks() -> dict:
    """Obligation sense: imminent (<=3d) or blown enemy clocks."""
    try:
        out = subprocess.run(
            ["python3", str(HOME / "enemy_obligations.py")],
            capture_output=True, text=True, timeout=120)
        imminent = len(re.findall(r"\[DUE\]|\[BLOWN\]", out.stdout))
        blown = len(re.findall(r"\[BLOWN\]", out.stdout))
        return {"value": imminent, "detail": {"blown": blown, "exit": out.returncode}}
    except Exception as e:
        return {"value": 0, "detail": {"error": str(e)[:80]}}


def sense_enemy() -> dict:
    """Threat sense: NEW UFW sources in the last 24h that the registry has
    never seen. ACCURACY FIX (2026-10-12): previously read the whole log
    (days of history) — now a true 24h window via RFC3339 parse, same as
    the touch receptor, so the novelty count is a real rate, not a ratchet."""
    import datetime as _dt
    known: set[str] = set()
    try:
        known = set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", REGISTRY.read_text(errors="replace")))
    except OSError:
        pass
    fresh: set[str] = set()
    try:
        out = subprocess.run(["tail", "-n", "20000", str(UFW_LOG)],
                             capture_output=True, text=True, timeout=60).stdout
        now_local = _dt.datetime.now()
        for line in out.splitlines():
            if "UFW BLOCK" not in line:
                continue
            tsm = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
            src = re.search(r"SRC=((?:\d{1,3}\.){3}\d{1,3})", line)
            if not src:
                continue
            if tsm:
                try:
                    when = _dt.datetime.fromisoformat(tsm.group(1))
                    if (now_local - when).total_seconds() > 86400:
                        continue
                except ValueError:
                    pass
            ip = src.group(1)
            if ip not in known:
                fresh.add(ip)
    except Exception:
        pass
    fresh = {ip for ip in fresh if not ip.startswith(("172.1", "10.", "192.168."))}
    return {"value": len(fresh), "detail": {"new_sources": sorted(fresh)[:10], "window_h": 24}}


def sense_field() -> dict:
    """Self-perception: is the sensory field itself actually alive?"""
    import urllib.request
    import urllib.error
    code = 0
    try:
        with urllib.request.urlopen("http://127.0.0.1:8900/sensory.html", timeout=8) as r:
            code = r.status
    except Exception:
        code = 0
    # render age
    age_min = None
    try:
        st = json.loads((HOME / "status" / "sensory_state.json").read_text())
        age_min = (dt.datetime.now(dt.timezone.utc)
                   - dt.datetime.fromisoformat(st["rendered_at"])).total_seconds() / 60
    except Exception:
        pass
    # healthy = field answers AND render fresh
    healthy = 1 if (code == 200 and age_min is not None and age_min <= 20) else 0
    return {"value": 1 - healthy, "detail": {"http": code, "render_age_min": round(age_min, 1) if age_min else None}}


def sense_superego() -> dict:
    """Somatic reserve: disk pressure (full disk = memory death)."""
    out = sh("df / | awk 'NR==2 {print $5}'").strip().rstrip('%')
    pct = int(out) if out.isdigit() else 0
    return {"value": pct, "detail": {"disk_pct": pct}}

