# Quantum qubit runtime

This repo now includes a small **classical qubit statevector runtime**.

It is not a hardware backend and it does not pretend to be one.
It is a controllable simulation layer for:

- Bell-state demos
- GHZ-style superposition demos
- branch/superposition experiments next to the cognition runtime
- small gate-sequence tests

## Files

- `quantum/qubit_runtime.py` — runtime implementation
- `run_qubit_runtime.py` — CLI runner

## Supported gates

Single-qubit:
- `H`
- `X`
- `Y`
- `Z`
- `S`
- `T`
- `RX`
- `RZ`

Two-qubit:
- `CX`
- `CZ`

## Default Bell-state demo

```bash
python run_qubit_runtime.py
```

That emits a 2-qubit Bell-state run with:
- nonzero amplitudes
- basis probabilities
- most-likely state
- Pauli-Z expectations
- sampled measurement counts

## Custom program format

A program is a JSON array of operations.

Example:

```json
[
  {"gate": "H", "qubit": 0},
  {"gate": "CX", "control": 0, "target": 1}
]
```

Run it with:

```bash
python run_qubit_runtime.py --qubits 2 --program my_program.json --shots 512
```

## Why it belongs here

The broader repo already works with:
- branches
- unresolved rival futures
- controlled collapse
- governed action under uncertainty

The qubit runtime gives the repo a compact sandbox for superposition-style experiments without pretending to be physical quantum hardware.

It is a simulation layer that fits the repo's larger interest in branch preservation and controlled collapse.
