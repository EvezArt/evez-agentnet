"""
daemon/loop.py — evez-agentnet
Main 24/7 daemon loop.

The task loop now commits an intent-state transition before and after execution,
so task routing is observable as a controller decision rather than an invisible
prompt heuristic.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

from daemon import builder, issue_queue, router, spine
from daemon.intent_state import IntentSignal, UserIntentState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("daemon.loop")

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))

SYSTEM_PROMPT = """You are the EVEZ autonomous agent daemon.
You receive task descriptions from GitHub Issues and produce concise,
actionable results. Be specific. Output markdown. Max 800 words."""


def _intent_for_task(title: str, body: str) -> UserIntentState:
    """Build a task-scoped intent state from observable task signals."""

    state = UserIntentState()

    signals = [
        IntentSignal(
            kind="task_title",
            value=title,
            weight=1.0,
            source="github_issue",
        ),
        IntentSignal(
            kind="task_body",
            value=body,
            weight=1.0 if body else 0.0,
            source="github_issue",
        ),
    ]

    objective = "build" if title.strip().startswith("[BUILD]") else "execute_task"
    state.set_explicit_objective(objective)
    state.observe(objective, signals)

    return state


def process_task(issue: dict) -> None:
    num = issue["number"]
    title = issue["title"]
    body = issue.get("body") or ""
    log.info("[loop] Processing issue #%s: %s", num, title)

    intent = _intent_for_task(title, body)

    spine.append(
        "task_start",
        {
            "issue": num,
            "title": title,
            "intent_state_hash": intent.state_hash(),
            "active_objective": intent.active_objective,
        },
    )
    spine.append_intent_state(
        intent,
        action="select_task_execution_path",
        result={"status": "selected"},
    )

    issue_queue.mark_running(num)

    try:
        if intent.active_objective == "build":
            action = "builder.handle_build_task"
            result = builder.handle_build_task(num, title, body)
        else:
            action = "router.complete"
            prompt = f"Task title: {title}\n\nTask details:\n{body}"
            result = router.complete(prompt, system=SYSTEM_PROMPT)
            if not result:
                result = "LLM returned no output. Please retry or add more detail."

        issue_queue.complete(num, result)

        intent.record_result(aligned=True)
        spine.append_intent_state(
            intent,
            action=action,
            result={
                "status": "completed",
                "aligned": True,
                "result_len": len(result),
            },
        )
        spine.append(
            "task_done",
            {
                "issue": num,
                "title": title,
                "result_len": len(result),
                "intent_state_hash": intent.state_hash(),
            },
        )
        log.info("[loop] Completed #%s", num)

    except Exception as exc:
        reason = f"Exception: {exc}"
        issue_queue.fail(num, reason)

        intent.record_result(aligned=False)
        spine.append_intent_state(
            intent,
            action="task_execution",
            result={
                "status": "failed",
                "aligned": False,
                "error": str(exc),
            },
            correction="execution failure",
        )
        spine.append(
            "task_failed",
            {
                "issue": num,
                "title": title,
                "error": str(exc),
                "intent_state_hash": intent.state_hash(),
            },
        )
        log.error("[loop] Failed #%s: %s", num, exc)


def ensure_spine_valid() -> tuple[int, str]:
    """Refuse execution when the append-only spine is already corrupted."""

    valid, checked, last_hash = spine.verify_chain()
    if not valid:
        raise RuntimeError(
            f"spine integrity check failed after {checked} events; "
            f"last trusted hash={last_hash}"
        )
    return checked, last_hash


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


def run_forever() -> None:
    log.info(
        "[loop] DAEMON starting. Poll interval: %ss",
        POLL_INTERVAL,
    )
    checked, last_hash = ensure_spine_valid()
    log.info("[loop] Spine verified: %s events, head=%s", checked, last_hash)
    issue_queue.ensure_labels()
    spine.append(
        "daemon_start",
        {
            "pid": os.getpid(),
            "spine_verified_events": checked,
            "spine_head_hash": last_hash,
        },
    )

    cycle_num = 0
    while True:
        cycle_num += 1
        log.info(
            "[loop] Cycle #%s @ %s",
            cycle_num,
            datetime.now(timezone.utc).isoformat(),
        )
        try:
            cycle()
        except Exception as exc:
            log.error("[loop] Cycle error: %s", exc)
            spine.append(
                "cycle_error",
                {"cycle": cycle_num, "error": str(exc)},
            )
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single cycle then exit",
    )
    args = parser.parse_args()

    issue_queue.ensure_labels()

    if args.once:
        n = cycle()
        sys.exit(0 if n >= 0 else 1)

    run_forever()
