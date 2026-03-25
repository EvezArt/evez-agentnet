"""
daemon/loop.py — evez-agentnet
Main 24/7 daemon loop.
Resolves: evez-agentnet#15

Polls GitHub Issues labeled 'daemon-task' every POLL_INTERVAL seconds.
Routes each task through OpenRouter LLM, writes result as issue comment,
closes issue. Self-building: [BUILD] tasks generate code + open PRs.

Usage:
  python -m daemon.loop             # run forever
  python -m daemon.loop --once      # single cycle (for Vercel/cron)

Env:
  GITHUB_TOKEN, OPENROUTER_API_KEY
  POLL_INTERVAL  — seconds between polls (default: 60)
  DAEMON_REPO    — default: EvezArt/evez-agentnet
"""
import os
import sys
import time
import logging
import argparse
from datetime import datetime, timezone

from daemon import issue_queue, router, builder, spine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("daemon.loop")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
SYSTEM_PROMPT = """You are the EVEZ autonomous agent daemon. 
You receive task descriptions from GitHub Issues and produce concise, 
actionable results. Be specific. Output markdown. Max 800 words."""


def process_task(issue: dict) -> None:
    num   = issue["number"]
    title = issue["title"]
    body  = issue.get("body") or ""
    log.info(f"[loop] Processing issue #{num}: {title}")

    spine.append("task_start", {"issue": num, "title": title})
    issue_queue.mark_running(num)

    try:
        if title.strip().startswith("[BUILD]"):
            result = builder.handle_build_task(num, title, body)
        else:
            prompt = f"Task title: {title}\n\nTask details:\n{body}"
            result = router.complete(prompt, system=SYSTEM_PROMPT)
            if not result:
                result = "⚠️ LLM returned no output. Please retry or add more detail."

        issue_queue.complete(num, result)
        spine.append("task_done", {"issue": num, "title": title, "result_len": len(result)})
        log.info(f"[loop] Completed #{num}")

    except Exception as e:
        reason = f"Exception: {e}"
        issue_queue.fail(num, reason)
        spine.append("task_failed", {"issue": num, "title": title, "error": str(e)})
        log.error(f"[loop] Failed #{num}: {e}")


def cycle() -> int:
    """Single poll cycle. Returns number of tasks processed."""
    tasks = issue_queue.dequeue(limit=3)
    if not tasks:
        log.info("[loop] No pending tasks.")
        spine.append("poll_empty", {"spine_count": spine.count()})
        return 0
    for task in tasks:
        process_task(task)
    return len(tasks)


def run_forever():
    log.info(f"[loop] DAEMON starting. Poll interval: {POLL_INTERVAL}s")
    issue_queue.ensure_labels()
    spine.append("daemon_start", {"pid": os.getpid()})
    cycle_num = 0
    while True:
        cycle_num += 1
        log.info(f"[loop] Cycle #{cycle_num} @ {datetime.now(timezone.utc).isoformat()}")
        try:
            cycle()
        except Exception as e:
            log.error(f"[loop] Cycle error: {e}")
            spine.append("cycle_error", {"cycle": cycle_num, "error": str(e)})
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single cycle then exit")
    args = parser.parse_args()
    issue_queue.ensure_labels()
    if args.once:
        n = cycle()
        sys.exit(0 if n >= 0 else 1)
    else:
        run_forever()
