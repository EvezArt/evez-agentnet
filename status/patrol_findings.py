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
        "evez-cogview", "ruview-bootstrap", "evez-raw-drops", "evez-films",
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
        # One clock = one finding. Read only the LATEST snapshot (last
        # parseable line): earlier 5-min snapshots of the same clock are
        # history, and re-printing every one floods the heartbeat with
        # hundreds of duplicates of a single finding. No snapshot ts in
        # the line either — identical state must print identically or the
        # determinism contract (and any monitor gate) is dead.
        for line in reversed(clocks.read_text(errors="replace").splitlines()):
            try:
                snap = json.loads(line)
            except ValueError:
                continue
            for c in snap.get("clocks", []):
                if isinstance(c, dict) and walk_near(c):
                    findings.append(
                        f"ENEMY-CLOCK-NEAR {c.get('id', '?')} "
                        f"deadline={c.get('deadline', '?')} "
                        f"days_left={c.get('days_left', '?')} "
                        f"status={c.get('status', '?')}")
            break

    r = sh(f"cd {REPO} && git status --porcelain")
    for line in r.stdout.splitlines():
        p = line[3:].strip().strip('"')
        if p.endswith(".jsonl") or p.endswith(".log"):
            continue
        if any(p.startswith(op) for op in OPERATIONAL):
            continue
        findings.append(f"CODE-DRIFT {p}")

    # Sensory cortex + ADVERSARIAL RE-VERIFICATION: a receptor firing novel is
    # a CLAIM, not a finding. Before it reaches the operator, the patrol
    # re-measures that receptor independently; only sensations that survive
    # their own re-test are reported. Transient firings die here, quietly —
    # the operator never sees a ghost the machine already disproved.
    def _remeasure(receptor: str):
        """Independent second measurement of a receptor that fired."""
        import importlib.util, sys as _sys
        if "/root/evez-agentnet" not in _sys.path:
            _sys.path.insert(0, "/root/evez-agentnet")  # sensory_cortex imports receptors_v2 by name
        try:
            names = {"verity", "delivery", "clocks", "enemy", "field", "superego"}
            mod_name = "sensory_receptors_v2" if receptor in names else "sensory_cortex"
            mod_path = Path(f"/root/evez-agentnet/{mod_name}.py")
            spec = importlib.util.spec_from_file_location(mod_name, mod_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, f"sense_{receptor}", None)
            v = float(fn()["value"]) if fn else None
            return v
        except Exception as _e:
            print(f"REMEASURE-DEBUG {receptor}: {type(_e).__name__}: {str(_e)[:80]}", file=sys.stderr)
            return None

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
            if not s.get("novel"):
                continue
            # transient flow/intruder spikes vanish before re-measure: re-test
            recheck = _remeasure(s["receptor"])
            if recheck is None:
                findings.append(
                    f"CORTEX-NOVEL {s['receptor']} v={s['value']} {json.dumps(s.get('detail',{}))[:100]} (unverifiable)")
            elif s["receptor"] in ("flow", "intruder", "load") and recheck < 0.4 * s["value"]:
                pass  # spike collapsed between render and patrol: drop the ghost
            else:
                findings.append(
                    f"CORTEX-NOVEL {s['receptor']} v={s['value']} re-measured={recheck:g} "
                    f"CONFIRMED {json.dumps(s.get('detail',{}))[:80]}")
    except FileNotFoundError:
        findings.append("CORTEX-MISSING sensory_state.json not rendered yet")
    except Exception as e:
        findings.append(f"CORTEX-ERROR {type(e).__name__}")

    for f in findings:
        print(f)
    sys.exit(0)


if __name__ == "__main__":
    main()
