#!/usr/bin/env python3
"""Validate local runtime/package versions against .evez-versions."""

from __future__ import annotations

import json
import pathlib
import sys
from importlib import metadata

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".evez-versions"

PACKAGE_NAME_MAP = {
    "python": None,
    "evez-os": None,
    "evez-agentnet": None,
    "openclaw": "openclaw",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "groq": "groq",
    "agno": "agno",
}


def read_contract() -> dict:
    if not CONTRACT.exists():
        raise FileNotFoundError(f"Missing contract file: {CONTRACT}")
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def installed_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def main() -> int:
    contract = read_contract()
    versions = contract.get("versions", {})
    failures: list[str] = []

    expected_python = versions.get("python")
    if expected_python:
        current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        if current_python != expected_python:
            failures.append(
                f"python expected {expected_python} but found {current_python}"
            )

    for key, expected in versions.items():
        mapped = PACKAGE_NAME_MAP.get(key)
        if mapped is None:
            continue
        current = installed_version(mapped)
        if current is None:
            failures.append(f"{key} expected {expected} but package is not installed")
            continue
        if current != expected:
            failures.append(f"{key} expected {expected} but found {current}")

    if failures:
        print("EVEZ version contract mismatch detected:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("EVEZ version contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
