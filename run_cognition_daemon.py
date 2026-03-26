from __future__ import annotations

import argparse
import json
from pathlib import Path

from cognition.checkpoint import CheckpointStore
from cognition.daemon import LivingLogicDaemon


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the restartable cognition daemon.")
    parser.add_argument("--state-dir", default=".state", help="Checkpoint directory")
    parser.add_argument("--input", help="Single input string to process")
    parser.add_argument("--input-file", help="Path to a text file of newline-separated events")
    args = parser.parse_args()

    store = CheckpointStore(args.state_dir)
    daemon = LivingLogicDaemon(store)

    events: list[str] = []
    if args.input:
        events.append(args.input)
    if args.input_file:
        events.extend(
            line.strip() for line in Path(args.input_file).read_text(encoding="utf-8").splitlines() if line.strip()
        )

    if not events:
        events.append("boot with no external event; preserve unresolved residue and remain rebootable")

    for event in events:
        result = daemon.step(event)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
