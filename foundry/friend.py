#!/usr/bin/env python3
"""Run the EVEZ-FRIEND local operator loop.

This is a continuity-aware assistant scaffold, not a claim of sentience.
It records user statements separately from model proposals and uses Hermes only
when a local Hermes CLI is available.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bridge.hermes import find_command, invoke as invoke_hermes
from runtime.memory import MemoryStore

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="generated evez-friend OS directory")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    memory = MemoryStore(root / "memory" / "events.jsonl")

    print("EVEZ-FRIEND")
    print("status: PROPOSED / local operator scaffold")
    print("commands: /memory <query>, /status, /exit")

    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        if line == "/exit":
            break
        if line == "/status":
            print(json.dumps({
                "os_id": manifest.get("os_id"),
                "generation": manifest.get("generation"),
                "objective": manifest.get("objective"),
                "memory_file": str(memory.path),
                "hermes": "available" if find_command() else "unavailable",
            }, indent=2))
            continue
        if line.startswith("/memory "):
            query = line[8:].strip()
            print(json.dumps(memory.search(query, limit=10), indent=2, ensure_ascii=False))
            continue

        user_item = memory.add("USER_STATEMENT", line, source="USER")
        recent = memory.search(line, limit=10)
        packet = {
            "os_id": manifest.get("os_id"),
            "objective": manifest.get("objective"),
            "user_statement": user_item,
            "relevant_memory": recent,
            "rules": [
                "separate user statement from inference",
                "do not invent memory",
                "mark uncertainty explicitly",
                "propose the next useful action",
            ],
        }

        result = invoke_hermes(packet, root)
        if result.get("status") != "OK":
            print("friend> Hermes unavailable; statement preserved as user memory.")
            continue

        proposal = result.get("output", "").strip()
        memory.add("PROPOSAL", proposal, source="HERMES")
        print("friend> " + proposal)

if __name__ == "__main__":
    main()
