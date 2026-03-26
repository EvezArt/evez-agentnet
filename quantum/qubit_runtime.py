#!/usr/bin/env python3
"""Small classical qubit runtime for evez-agentnet.

This is a statevector simulator, not a hardware backend.
It is useful for:
- Bell/GHZ demonstrations
- controlled branch experiments
- cognition-adjacent quantum-style superposition demos
"""

from __future__ import annotations

import cmath
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


Complex = complex


def _format_complex(z: Complex, precision: int = 6) -> str:
    r = round(z.real, precision)
    i = round(z.imag, precision)
    if i == 0:
        return str(r)
    if r == 0:
        return f"{i}j"
    sign = "+" if i >= 0 else "-"
    return f"{r}{sign}{abs(i)}j"


@dataclass
class MeasurementResult:
    bitstring: str
    probability: float

    def to_dict(self) -> dict:
        return {"bitstring": self.bitstring, "probability": self.probability}


class QubitRuntime:
    def __init__(self, qubits: int) -> None:
        if qubits <= 0:
            raise ValueError("qubits must be >= 1")
        self.qubits = qubits
        self.dimension = 1 << qubits
        self.state: list[Complex] = [0j] * self.dimension
        self.state[0] = 1 + 0j
        self.history: list[dict] = []

    def _validate_qubit(self, index: int) -> None:
        if not 0 <= index < self.qubits:
            raise IndexError(f"qubit index {index} out of range for {self.qubits} qubits")

    def _apply_single_qubit_gate(self, qubit: int, gate: list[list[Complex]], name: str) -> None:
        self._validate_qubit(qubit)
        step = 1 << qubit
        block = step << 1
        for start in range(0, self.dimension, block):
            for offset in range(step):
                i0 = start + offset
                i1 = i0 + step
                a0 = self.state[i0]
                a1 = self.state[i1]
                self.state[i0] = gate[0][0] * a0 + gate[0][1] * a1
                self.state[i1] = gate[1][0] * a0 + gate[1][1] * a1
        self.history.append({"gate": name, "qubit": qubit})

    def _apply_controlled_x(self, control: int, target: int) -> None:
        self._validate_qubit(control)
        self._validate_qubit(target)
        if control == target:
            raise ValueError("control and target must differ")
        for index in range(self.dimension):
            if ((index >> control) & 1) == 1 and ((index >> target) & 1) == 0:
                swap_index = index | (1 << target)
                self.state[index], self.state[swap_index] = self.state[swap_index], self.state[index]
        self.history.append({"gate": "CX", "control": control, "target": target})

    def _apply_controlled_z(self, control: int, target: int) -> None:
        self._validate_qubit(control)
        self._validate_qubit(target)
        if control == target:
            raise ValueError("control and target must differ")
        for index in range(self.dimension):
            if ((index >> control) & 1) == 1 and ((index >> target) & 1) == 1:
                self.state[index] *= -1
        self.history.append({"gate": "CZ", "control": control, "target": target})

    def x(self, qubit: int) -> None:
        self._apply_single_qubit_gate(qubit, [[0, 1], [1, 0]], "X")

    def y(self, qubit: int) -> None:
        self._apply_single_qubit_gate(qubit, [[0, -1j], [1j, 0]], "Y")

    def z(self, qubit: int) -> None:
        self._apply_single_qubit_gate(qubit, [[1, 0], [0, -1]], "Z")

    def h(self, qubit: int) -> None:
        s = 1 / math.sqrt(2)
        self._apply_single_qubit_gate(qubit, [[s, s], [s, -s]], "H")

    def s(self, qubit: int) -> None:
        self._apply_single_qubit_gate(qubit, [[1, 0], [0, 1j]], "S")

    def t(self, qubit: int) -> None:
        self._apply_single_qubit_gate(qubit, [[1, 0], [0, cmath.exp(1j * math.pi / 4)]], "T")

    def rx(self, qubit: int, theta: float) -> None:
        c = math.cos(theta / 2)
        s = -1j * math.sin(theta / 2)
        self._apply_single_qubit_gate(qubit, [[c, s], [s, c]], "RX")
        self.history[-1]["theta"] = theta

    def rz(self, qubit: int, theta: float) -> None:
        self._apply_single_qubit_gate(
            qubit,
            [[cmath.exp(-1j * theta / 2), 0], [0, cmath.exp(1j * theta / 2)]],
            "RZ",
        )
        self.history[-1]["theta"] = theta

    def cx(self, control: int, target: int) -> None:
        self._apply_controlled_x(control, target)

    def cz(self, control: int, target: int) -> None:
        self._apply_controlled_z(control, target)

    def probabilities(self) -> list[float]:
        return [abs(amplitude) ** 2 for amplitude in self.state]

    def amplitudes(self) -> dict[str, str]:
        result = {}
        for index, amplitude in enumerate(self.state):
            if abs(amplitude) > 1e-12:
                result[self._basis_label(index)] = _format_complex(amplitude)
        return result

    def _basis_label(self, index: int) -> str:
        return format(index, f"0{self.qubits}b")

    def sample(self, shots: int = 1024) -> dict[str, int]:
        if shots <= 0:
            raise ValueError("shots must be > 0")
        probs = self.probabilities()
        labels = [self._basis_label(i) for i in range(self.dimension)]
        counts = Counter(random.choices(labels, weights=probs, k=shots))
        return dict(sorted(counts.items()))

    def most_likely(self) -> MeasurementResult:
        probs = self.probabilities()
        index = max(range(len(probs)), key=lambda i: probs[i])
        return MeasurementResult(self._basis_label(index), probs[index])

    def expectation_z(self, qubit: int) -> float:
        self._validate_qubit(qubit)
        total = 0.0
        for index, prob in enumerate(self.probabilities()):
            total += prob if ((index >> qubit) & 1) == 0 else -prob
        return total

    def reset(self) -> None:
        self.state = [0j] * self.dimension
        self.state[0] = 1 + 0j
        self.history.clear()

    def to_dict(self) -> dict:
        return {
            "qubits": self.qubits,
            "history": self.history,
            "amplitudes": self.amplitudes(),
            "probabilities": {
                self._basis_label(i): round(p, 6) for i, p in enumerate(self.probabilities()) if p > 1e-12
            },
            "most_likely": self.most_likely().to_dict(),
            "z_expectations": {str(q): round(self.expectation_z(q), 6) for q in range(self.qubits)},
        }

    def run_program(self, operations: Iterable[dict]) -> dict:
        for op in operations:
            gate = op["gate"].upper()
            if gate == "H":
                self.h(op["qubit"])
            elif gate == "X":
                self.x(op["qubit"])
            elif gate == "Y":
                self.y(op["qubit"])
            elif gate == "Z":
                self.z(op["qubit"])
            elif gate == "S":
                self.s(op["qubit"])
            elif gate == "T":
                self.t(op["qubit"])
            elif gate == "RX":
                self.rx(op["qubit"], float(op["theta"]))
            elif gate == "RZ":
                self.rz(op["qubit"], float(op["theta"]))
            elif gate == "CX":
                self.cx(op["control"], op["target"])
            elif gate == "CZ":
                self.cz(op["control"], op["target"])
            else:
                raise ValueError(f"unsupported gate: {gate}")
        return self.to_dict()


def bell_state_demo() -> dict:
    runtime = QubitRuntime(2)
    runtime.h(0)
    runtime.cx(0, 1)
    result = runtime.to_dict()
    result["samples_256"] = runtime.sample(256)
    return result


if __name__ == "__main__":
    demo = bell_state_demo()
    print(json.dumps(demo, indent=2))
