#!/usr/bin/env python3
"""
daemon/run_forever.py — evez-agentnet 24/7 Free Runtime Daemon
===============================================================
Resolves: #15 [DAEMON] 24/7 Free Runtime Self-Building AI Agent Bus

Runs the orchestrator in an infinite restart loop with exponential backoff.
Suitable for Railway free-tier, Replit, or any process supervisor.

Usage:
  python daemon/run_forever.py

Env vars:
  ROUND_INTERVAL  = seconds between rounds (default 1800)
  MAX_BACKOFF     = max seconds to wait after crash (default 300)
  REPORT_EMAIL    = email for crash alerts (optional)
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daemon")

RESTART_LOG = Path("logs/restarts.jsonl")
RESTART_LOG.parent.mkdir(exist_ok=True)

MAX_BACKOFF  = int(os.environ.get("MAX_BACKOFF", "300"))
ROUND_INTERVAL = int(os.environ.get("ROUND_INTERVAL", "1800"))


def record_restart(reason: str, backoff: int):
    import json
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "reason": reason, "backoff_s": backoff}
    with open(RESTART_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    crash_count = 0
    while True:
        log.info(f"[daemon] Starting orchestrator (run #{crash_count + 1})")
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "orchestrator"],
                timeout=ROUND_INTERVAL + 120,
            )
            if proc.returncode == 0:
                crash_count = 0
                log.info("[daemon] Round completed cleanly.")
            else:
                raise RuntimeError(f"exit code {proc.returncode}")
        except Exception as e:
            crash_count += 1
            backoff = min(2 ** crash_count, MAX_BACKOFF)
            log.error(f"[daemon] Crash #{crash_count}: {e}. Restarting in {backoff}s...")
            record_restart(str(e), backoff)
            time.sleep(backoff)


if __name__ == "__main__":
    main()
