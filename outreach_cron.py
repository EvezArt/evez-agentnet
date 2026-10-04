#!/usr/bin/env python3
"""Runs the outreach agent on a cadence and appends a run-summary receipt.

Deliberately conservative: a run every 30 minutes. Volume buys nothing on
social platforms and gets accounts rate-limited or banned. What compounds is
being findable, which is why ARBITER audits HN findability every cycle.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

INTERVAL = int(__import__("os").environ.get("OUTREACH_INTERVAL", "1800"))
SUMMARY = Path(__file__).parent / "evidence" / "outreach_last_run.json"


def main() -> None:
    while True:
        started = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "outreach_agent.py")],
                capture_output=True, text=True, timeout=120,
            )
            summary = {"ok": proc.returncode == 0, "returncode": proc.returncode,
                       "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-1000:]}
        except Exception as e:
            summary = {"ok": False, "error": str(e)}
        summary["started"] = started
        summary["finished"] = time.time()
        summary["at"] = datetime.now(timezone.utc).isoformat()
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(summary, indent=2))
        print(f"[outreach-cron] run ok={summary.get('ok')} at {summary['at']}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
