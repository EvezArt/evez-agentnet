#!/usr/bin/env python3
"""Canonical bootstrap for evez-agentnet.

Defaults to the strongest cognition-governed entrypoint instead of the legacy loop.
Set AGENTNET_MODE to one of:
- legacy
- native
- full
- governed
- status
- proof
"""

from __future__ import annotations

import importlib
import os
import time

MODE = os.environ.get("AGENTNET_MODE", "governed").strip().lower()
ROUND_INTERVAL = int(os.environ.get("ROUND_INTERVAL", "1800"))

MODULES = {
    "legacy": "orchestrator",
    "native": "orchestrator_cognition_native",
    "full": "orchestrator_cognition_full",
    "governed": "orchestrator_cognition_governed",
    "status": "cognition_status",
    "proof": "cognition_proof",
}


def main() -> None:
    module_name = MODULES.get(MODE, MODULES["governed"])
    module = importlib.import_module(module_name)

    if MODE in {"status", "proof"}:
        module.main()
        return

    while True:
        module.main()
        print(f"[run_agentnet] mode={MODE} sleeping {ROUND_INTERVAL}s")
        time.sleep(ROUND_INTERVAL)


if __name__ == "__main__":
    main()
