#!/usr/bin/env python3
"""
EVEZ JEV — command line for the System One decision layer.

    python3 jev_cli.py status              # is it configured?
    python3 jev_cli.py probe               # one noul against arbitrary state
    python3 jev_cli.py attention           # which agent needs help?
    python3 jev_cli.py shipper             # is the shipper broken or just idle?
    python3 jev_cli.py escalate "<text>"   # should a human be paged?
    python3 jev_cli.py health              # full stack state for a judgement

Requires TYPESAFE_API_KEY for anything but `status`/`health`.

Design note: every command prints `source: fallback` explicitly when Jev is
unavailable. It never prints a plausible-looking number it did not receive.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).parent
sys.path.insert(0, str(REPO))

import jev_decisions as JD                      # noqa: E402
from jev_client import JevUnavailable, evaluate  # noqa: E402

STATE_FILE = REPO / "worldsim/worldsim_state.json"
BRIEF_FILE = REPO / "status/BRIEF.md"
HEALTH_FILE = REPO / "status/HEALTH.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"round": 0, "agents": {}, "maes": {}, "total_earned_usd": 0.0}


def show(obj) -> None:
    print(json.dumps(obj, indent=1, default=str))


def cmd_status(_a):
    s = JD.status()
    show(s)
    if not s["available"]:
        print("\nNOT CONFIGURED. To enable:")
        print("  1. Request early access at typesafe.ai")
        print("  2. export TYPESAFE_API_KEY=<key>")
        print("  3. re-run: python3 jev_cli.py probe")
        print("\nUntil then every decision returns an explicit fallback.")
        return 0
    print("\nready — decisions will be live and logged to jev/decisions.jsonl")
    return 0


def cmd_health(_a):
    st = load_state()
    show({
        "round": st.get("round"),
        "total_earned_usd": st.get("total_earned_usd", 0.0),
        "agents": {k: {"rep": round(v.get("reputation", 0), 3),
                       "tasks": v.get("tasks_completed", 0),
                       "streak": v.get("streak", 0)}
                   for k, v in (st.get("agents") or {}).items()},
        "maes": st.get("maes", {}),
    })
    return 0


def cmd_probe(a):
    questions = {
        a.name: {
            "type": "noul",
            "instructions": a.question,
            "criteria": {"true": "yes", "false": "no"},
        }
    }
    try:
        ans = evaluate(a.state, questions)
    except JevUnavailable as e:
        show({"ok": False, "source": "fallback", "reason": str(e)})
        return 1
    k, v = next(iter(ans.items()))
    show({"ok": True, "source": "jev", "model": v.model,
          "question": a.name, "probability": v.noul,
          "verdict": (v.noul or 0) >= JD.YES_THRESHOLD,
          "threshold": JD.YES_THRESHOLD})
    return 0


def cmd_attention(_a):
    show(JD.judge_attention_target(load_state()))
    return 0


def cmd_shipper(_a):
    show(JD.judge_shipper_health(load_state()))
    return 0


def cmd_advice(a):
    """Show this round's JEV advice as recorded by the OODA loop."""
    import jev_integration as JI
    try:
        state = load_state()
    except Exception:
        state = {"round": 0, "agents": {}, "maes": {}}
    adv = JI.advise(state, state.get("round", 0))
    show(adv)
    print("\n" + JI.summarise(adv))
    return 0


def cmd_escalate(a):
    brief = BRIEF_FILE.read_text(errors="replace") if BRIEF_FILE.exists() else ""
    health = {}
    if HEALTH_FILE.exists():
        try:
            health = json.loads(HEALTH_FILE.read_text())
        except json.JSONDecodeError:
            health = {}
    text = (a.text + "\n\n" + brief) if a.text else brief
    show(JD.judge_escalation(text, health))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="jev_cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="configuration + readiness").set_defaults(fn=cmd_status)
    sub.add_parser("health", help="print current stack state").set_defaults(fn=cmd_health)
    sub.add_parser("attention", help="which agent needs intervention").set_defaults(fn=cmd_attention)
    sub.add_parser("shipper", help="is the shipper broken or just idle?").set_defaults(fn=cmd_shipper)
    sub.add_parser("advice", help="run JEV advice for the current round").set_defaults(fn=cmd_advice)

    pr = sub.add_parser("probe", help="one ad-hoc noul question")
    pr.add_argument("state", help="the state to evaluate")
    pr.add_argument("question", help="the yes/no question")
    pr.add_argument("--name", default="probe", help="question id")
    pr.set_defaults(fn=cmd_probe)

    pe = sub.add_parser("escalate", help="should a human be paged?")
    pe.add_argument("text", nargs="?", default="", help="extra context")
    pe.set_defaults(fn=cmd_escalate)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
