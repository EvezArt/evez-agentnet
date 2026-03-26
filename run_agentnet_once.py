#!/usr/bin/env python3
"""One-shot launcher for evez-agentnet modes.

Useful for dry runs, CI, and inspecting a single governed cognition round
without starting an endless loop.
"""

from __future__ import annotations

import importlib
import os

MODE = os.environ.get("AGENTNET_MODE", "governed").strip().lower()

MODULES = {
    "legacy": "orchestrator",
    "native": "orchestrator_cognition_native",
    "full": "orchestrator_cognition_full",
    "governed": "orchestrator_cognition_governed",
    "status": "cognition_status",
    "proof": "cognition_proof",
    "receipt": "cognition_receipt",
    "dashboard": "cognition_dashboard_governed",
}


def main() -> None:
    module_name = MODULES.get(MODE, MODULES["governed"])
    module = importlib.import_module(module_name)
    module.main()


if __name__ == "__main__":
    main()
