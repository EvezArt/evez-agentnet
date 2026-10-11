#!/usr/bin/env python3
"""Patrol tripwire — the heartbeat's healed form.

Prints ONLY real findings, one per line. Empty output means the grid is
green and the agent is never woken. Deterministic by design: no timestamps,
no drifting counts, so an unchanged grid produces identical (empty) output
and the monitor gate keeps the agent asleep. Speech costs evidence.
"""
import subprocess
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/root/evez-agentnet")
EVID = REPO / "evidence" / datetime.now(timezone.utc).strftime("%Y-%m-%d")

OPERATIONAL = (
    "evidence/", "spine/", "logs/", "drafts/", ".state/", "lineage/",
    "eye/", "proof/", "predictor/", "scanner/", "shipper/", "worldsim/",
    "forge_output/", "status/", "ruview_tailnet/",
)
SUITES = [
    "audit_repo.py", "verify_spine.py", "test_cognition_deltas.py",
    "test_delta_ingest.py", "forest_verify.py", "test_audit_detects.py",
    "test_exposure_watchdog.py",
]


def sh(cmd, timeout=120):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def walk_near(o):
    if isinstance(o, dict):
        if "days_left" in o:
            try:
                if float(o["days_left"]) <= 3:
                    return True
            except (TypeError, ValueError):
                pass
        return any(walk_near(v) for v in o.values())
    if isinstance(o, list):
        return any(walk_near(v) for v in o)
    return False


def main():
    findings = []

    for s in SUITES:
        try:
            r = sh(f"cd {REPO} && python3 {s}", timeout=300)
            if r.returncode != 0:
                tail = (r.stdout + r.stderr).strip().splitlines()
                findings.append(f"TEST-FAIL {s} :: {tail[-1][:160] if tail else 'no output'}")
        except subprocess.TimeoutExpired:
            findings.append(f"TEST-TIMEOUT {s}")

    r = sh("systemctl --failed --no-legend")
    for line in r.stdout.strip().splitlines():
        if line.strip():
            findings.append(f"UNIT-FAILED {line.split()[0]}")

    # Expected-services liveness: a unit that is merely "inactive" is invisible
    # to --failed but still an outage if it is supposed to be running. The
    # evez-agentnet OODA loop ran dead for 11 hours under exactly this blind
    # spot on 2026-10-11 (never enabled, died silently, patrol saw nothing).
    EXPECTED_UNITS = [
        "evez-agentnet", "evez-event-spine", "openclaw-gateway",
        "evez-cogview", "ruview-bootstrap",
    ]
    for unit in EXPECTED_UNITS:
        out = sh(f"systemctl is-active {unit}").stdout.strip()
        if out != "active":
            findings.append(f"UNIT-NOT-LIVE {unit} state={out}")

    r = sh("docker ps --format '{{.Names}} {{.Status}}'")
    if r.returncode == 0:
        for line in r.stdout.splitlines():
            if "unhealthy" in line:
                findings.append(f"DOCKER-UNHEALTHY {line.strip()}")

    r = sh("ss -H -tln")
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local = parts[3]
            if local.endswith(":18789") or local.endswith(":4222"):
                addr = local.rsplit(":", 1)[0]
                if addr not in ("127.0.0.1", "[::1]", "::1", "localhost"):
                    findings.append(f"PERIMETER-BREACH {local}")

    exp = EVID / "exposure.jsonl"
    if exp.exists():
        lines = exp.read_text(errors="replace").strip().splitlines()[-50:]
        hot = [l for l in lines if re.search(r'"severity":\s*"(ERROR|WARN|FATAL)"', l)]
        if hot:
            findings.append(f"EXPOSURE-HOT {len(hot)} non-INFO rows in evidence tail")

    clocks = EVID / "enemy_clocks.jsonl"
    if clocks.exists():
        for line in clocks.read_text(errors="replace").splitlines():
            try:
                if walk_near(json.loads(line)):
                    findings.append(f"ENEMY-CLOCK-NEAR {line[:160]}")
            except ValueError:
                continue

    r = sh(f"cd {REPO} && git status --porcelain")
    for line in r.stdout.splitlines():
        p = line[3:].strip().strip('"')
        if p.endswith(".jsonl") or p.endswith(".log"):
            continue
        if any(p.startswith(op) for op in OPERATIONAL):
            continue
        findings.append(f"CODE-DRIFT {p}")

    # Sensory cortex: any receptor firing novel stimulus is a finding —
    # the patrol reads what the machine FEELS, not just what it computes.
    try:
        sc = json.loads(Path("/root/evez-agentnet/status/sensory_state.json").read_text())
        age_min = None
        try:
            import datetime as _dt
            age_min = (_dt.datetime.now(_dt.timezone.utc)
                       - _dt.datetime.fromisoformat(sc["rendered_at"])).total_seconds() / 60
        except Exception:
            pass
        if age_min is None or age_min > 20:
            findings.append(f"CORTEX-STALE rendered_at={sc.get('rendered_at','?')}")
        for s in sc.get("sensations", []):
            if s.get("novel"):
                findings.append(
                    f"CORTEX-NOVEL {s['receptor']} v={s['value']} {json.dumps(s.get('detail',{}))[:100]}")
    except FileNotFoundError:
        findings.append("CORTEX-MISSING sensory_state.json not rendered yet")
    except Exception as e:
        findings.append(f"CORTEX-ERROR {type(e).__name__}")

    for f in findings:
        print(f)
    sys.exit(0)


if __name__ == "__main__":
    main()
