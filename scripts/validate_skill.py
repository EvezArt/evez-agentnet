#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

REQUIRED_KEYS = [
    "id:",
    "name:",
    "version:",
    "schema:",
    "runtime:",
    "capabilities:",
    "fire_events:",
    "dependencies:",
    "auth:",
    "termux:",
]


def main() -> int:
    skill_path = pathlib.Path("SKILL.md")
    if not skill_path.exists():
        print("Missing SKILL.md")
        return 1

    content = skill_path.read_text(encoding="utf-8")
    missing = [key for key in REQUIRED_KEYS if key not in content]
    if missing:
        print("SKILL.md missing required keys:")
        for key in missing:
            print(f" - {key}")
        return 1

    print("SKILL.md v2 structure looks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
