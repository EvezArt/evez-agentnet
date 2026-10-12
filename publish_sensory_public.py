#!/usr/bin/env python3
"""Publish the sensory field's live snapshot to the public mirror.

Strips the cortex state to receptor-name/value/novelty only — no hosts,
no source IPs, no internals — and pushes to EvezArt/evezart.github.io
(sensory-data.json) so the field is viewable from any browser, not just
the tailnet. Runs on cron; pushes only when the snapshot content changed.
"""
import json, subprocess, sys
from pathlib import Path

STATE = Path("/root/evez-agentnet/status/sensory_state.json")
CLONE = Path("/root/.cache/sensory-public")

def main() -> int:
    s = json.loads(STATE.read_text())
    pub = {
        "tick": s["tick"],
        "rendered_at": s["rendered_at"],
        "sensations": [
            {"receptor": x["receptor"], "value": x["value"], "novel": x["novel"]}
            for x in s.get("sensations", [])
        ],
    }
    CLONE.mkdir(parents=True, exist_ok=True)
    def run(cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=CLONE)
    if not (CLONE / ".git").exists():
        r = run("gh repo clone EvezArt/evezart.github.io . -- --depth 1")
        if r.returncode != 0:
            print("clone failed:", r.stderr[:120]); return 1
    run("git pull --rebase -q")
    old = (CLONE / "sensory-data.json").read_text() if (CLONE / "sensory-data.json").exists() else ""
    new = json.dumps(pub, indent=1)
    if old == new:
        print("no change; skip")
        return 0
    (CLONE / "sensory-data.json").write_text(new)
    run("git add sensory-data.json && git commit -q -m 'sensory snapshot tick " + str(pub["tick"]) + "'")
    r = run("git push -q origin main")
    ok = r.returncode == 0
    print("pushed" if ok else f"push failed: {r.stderr[:120]}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
