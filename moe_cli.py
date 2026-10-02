#!/usr/bin/env python3
"""
EVEZ MoE — command line.

    python3 moe_cli.py roster                    # what experts actually exist
    python3 moe_cli.py route "classify this"      # which expert, and why
    python3 moe_cli.py ask "..." --kind summarise # route + generate
    python3 moe_cli.py cost "..." --kind classify # route + cost, no generation
    python3 moe_cli.py routes                     # routing history
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from moe_infer import generate                      # noqa: E402
from moe_router import ROUTER_LOG, route, status    # noqa: E402


def show(o):
    print(json.dumps(o, indent=1, default=str))


def cmd_roster(_a):
    s = status()
    print(f"Ollama {s['ollama']} — reachable: {s['reachable']}\n")
    if not s["experts"]:
        print("No experts discovered. Routing will fail loudly.")
        return 1
    for n, e in sorted(s["experts"].items(), key=lambda kv: kv[1]["mb"]):
        role = "EMBED ONLY" if "embed" in n else "generative"
        print(f"  {n:28} {e['params']:>10}  {e['mb']:>5}MB  {role}")
    print(f"\nJev gate: {'enabled' if s['jev_gate'] else 'disabled (no API key)'}")
    print(f"Task kinds: {', '.join(s['task_kinds'])}")
    return 0


def cmd_route(a):
    r = route(a.text, prefer=a.kind)
    show({"expert": r.expert, "task_kind": r.task_kind, "gate": r.gate,
          "reason": r.reason, "confidence": r.confidence,
          "candidates": r.candidates})
    return 0 if r.expert else 1


def cmd_ask(a):
    r = generate(a.text, prefer=a.kind)
    if not r.get("ok"):
        show({"error": r.get("error"), "expert": r.get("expert"),
              "gate": r.get("gate")})
        return 1
    print(f"[{r['expert']} · {r['task_kind']} · {r['elapsed_s']}s · "
          f"{r.get('eval_count')} tok]\n")
    print(r["text"])
    return 0


def cmd_cost(a):
    """Show what a route WOULD cost, without paying for generation."""
    r = route(a.text, prefer=a.kind)
    if not r.expert:
        show({"error": r.reason})
        return 1
    s = status()
    e = s["experts"].get(r.expert, {})
    alts = list(r.candidates)
    show({
        "expert": r.expert,
        "params": e.get("params"),
        "size_mb": e.get("mb"),
        "gate": r.gate,
        "reason": r.reason,
        "escalation_path": [
            {"expert": c, "params": s["experts"].get(c, {}).get("params"),
             "mb": s["experts"].get(c, {}).get("mb")} for c in alts],
    })
    return 0


def cmd_routes(_a):
    if not ROUTER_LOG.exists():
        print("no routes logged yet")
        return 0
    rows = [json.loads(l) for l in ROUTER_LOG.read_text().splitlines() if l.strip()]
    print(f"{len(rows)} routes logged\n")
    for r in rows[-15:]:
        print(f"  {r['ts'][:19]}  {str(r['expert']):28} "
              f"{r['task_kind']:10} {r['gate']:14} {r['reason'][:44]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="moe_cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("roster", help="experts actually installed").set_defaults(fn=cmd_roster)
    sub.add_parser("routes", help="routing history").set_defaults(fn=cmd_routes)

    pr = sub.add_parser("route", help="pick an expert, no generation")
    pr.add_argument("text")
    pr.add_argument("--kind", default=None)
    pr.set_defaults(fn=cmd_route)

    pa = sub.add_parser("ask", help="route + generate")
    pa.add_argument("text")
    pa.add_argument("--kind", default=None)
    pa.set_defaults(fn=cmd_ask)

    pc = sub.add_parser("cost", help="show route cost, no generation")
    pc.add_argument("text")
    pc.add_argument("--kind", default=None)
    pc.set_defaults(fn=cmd_cost)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
