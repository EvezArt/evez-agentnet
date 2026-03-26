#!/usr/bin/env python3
"""Supervisory launcher for evez-agentnet.

Runs the governed cognition entrypoint and then emits proof, receipt,
and HTML dashboard artifacts after each round.
"""

from __future__ import annotations

import importlib
import os
import time

ROUND_INTERVAL = int(os.environ.get('ROUND_INTERVAL', '1800'))


def main() -> None:
    governed = importlib.import_module('orchestrator_cognition_governed')
    proof = importlib.import_module('cognition_proof')
    receipt = importlib.import_module('cognition_receipt')
    dashboard = importlib.import_module('cognition_dashboard_governed')

    while True:
        governed.main()
        proof.main()
        receipt.main()
        dashboard.main()
        print(f'[run_agentnet_supervised] sleeping {ROUND_INTERVAL}s')
        time.sleep(ROUND_INTERVAL)


if __name__ == '__main__':
    main()
