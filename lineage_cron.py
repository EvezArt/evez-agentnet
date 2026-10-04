#!/usr/bin/env python3
"""Seals a lineage generation block on a cadence and republishes the runbook.

Sealing is cheap and append-only, so it runs often: every 6 hours. Each block
captures the swarm's live state, chains to the previous hash, and is announced
on the event spine. A block can never be edited, only superseded.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
INTERVAL = int(__import__("os").environ.get("LINEAGE_INTERVAL", "21600"))  # 6h
LOG = ROOT / "evidence" / "lineage_seals.jsonl"


def main() -> None:
    while True:
        try:
            sys.path.insert(0, str(ROOT))
            import lineage
            block = lineage.seal_generation("scheduled")
            chain = lineage.verify_chain()
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a") as f:
                f.write(json.dumps({
                    "generation": block["generation"],
                    "name": block["generation_name"],
                    "hash": block["hash"],
                    "spine_seq": block.get("spine_event"),
                    "chain_valid": chain["chain_valid"],
                    "at": block["iso"],
                }) + "\n")
            # Regenerate the runbook so it always reflects the newest block.
            subprocess.run([sys.executable, str(ROOT / "cold_start.py")],
                           capture_output=True, timeout=60)
            print(f"[lineage] sealed {block['generation_name']} "
                  f"valid={chain['chain_valid']} at {block['iso']}", flush=True)
        except Exception as e:
            print(f"[lineage] error: {e}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
