#!/usr/bin/env python3
"""Run the classical qubit runtime.

Examples:
  python run_qubit_runtime.py
  python run_qubit_runtime.py --qubits 3 --program demo/quantum_ghz_program.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from quantum.qubit_runtime import QubitRuntime, bell_state_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the qubit runtime statevector simulator.")
    parser.add_argument("--qubits", type=int, default=2, help="Number of qubits for custom programs")
    parser.add_argument("--program", help="Path to a JSON file containing a list of gate operations")
    parser.add_argument("--shots", type=int, default=256, help="Number of measurement samples to draw")
    args = parser.parse_args()

    if not args.program:
        print(json.dumps(bell_state_demo(), indent=2))
        return

    operations = json.loads(Path(args.program).read_text(encoding="utf-8"))
    runtime = QubitRuntime(args.qubits)
    result = runtime.run_program(operations)
    result["samples"] = runtime.sample(args.shots)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
