from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

def find_command() -> str | None:
    return shutil.which("hermes-agent") or shutil.which("hermes")

def invoke(packet: dict, root: Path) -> dict:
    command = find_command()
    if not command:
        return {"status": "UNAVAILABLE", "reason": "Hermes CLI not found"}

    prompt = {
        "role": "EVEZ Foundry architecture reviewer",
        "contract": [
            "Treat repository capability claims as PROPOSED until source evidence supports them.",
            "Do not fabricate execution, benchmarks, credentials, endpoints, or external state.",
            "Return UNKNOWN when evidence is insufficient.",
            "Propose the next highest-information-gain probe.",
        ],
        "packet": packet,
    }
    payload = json.dumps(prompt, ensure_ascii=False)

    if Path(command).name == "hermes-agent":
        args = [command, "--query-file", "-", "--oneshot", "--quiet"]
    else:
        args = [command, "chat", "--query-file", "-", "--oneshot", "--quiet"]

    try:
        result = subprocess.run(
            args,
            input=payload,
            text=True,
            capture_output=True,
            cwd=root,
            timeout=int(os.getenv("EVEZ_HERMES_TIMEOUT", "900")),
            check=False,
        )
    except Exception as exc:
        return {"status": "ERROR", "error": type(exc).__name__}

    return {
        "status": "OK" if result.returncode == 0 else "ERROR",
        "returncode": result.returncode,
        "output": result.stdout[-50000:],
        "stderr": result.stderr[-10000:],
    }
