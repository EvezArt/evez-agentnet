#!/usr/bin/env python3
"""Single mobile-friendly command front door for the EVEZ Foundry."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

COMMANDS = {
    "inventory": ["inventory.py"],
    "inspect": ["inspect_repo.py"],
    "extract": ["extract_capabilities.py"],
    "assemble": ["assemble.py"],
    "generate": ["generate_os.py"],
    "audit": ["audit_corpus.py"],
    "cycle": ["cycle.py"],
    "evaluate": ["evaluate.py"],
    "replicate": ["replicate.py"],
    "adversary": ["adversary.py"],
    "supervisor": ["supervisor.py"],
    "friend": ["friend.py"],
}

def main():
    parser = argparse.ArgumentParser(description="EVEZ Agentic OS Foundry")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    script = ROOT / COMMANDS[ns.command][0]
    result = subprocess.run(
        [sys.executable, str(script), *ns.args],
        cwd=REPO,
        text=True,
        check=False,
    )
    raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
