from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

def find_command() -> str | None:
    return shutil.which("openclaw")

def invoke(task_file: Path, root: Path) -> dict:
    if os.getenv("EVEZ_OPENCLAW_EXEC", "0") != "1":
        return {"status": "DISABLED", "reason": "EVEZ_OPENCLAW_EXEC is not 1"}

    command = find_command()
    if not command:
        return {"status": "UNAVAILABLE", "reason": "OpenClaw CLI not found"}

    prompt = (
        "Read the supplied Foundry task. Work only inside the designated isolated "
        "workspace. Do not deploy, delete remote data, rotate credentials, merge, "
        "publish, make financial/legal actions, or contact external parties. "
        "Capture observed results and failures. Return an evidence summary.\n\n"
        f"Task file: {task_file}"
    )
    args = [command, "agent", "exec", prompt, "--cwd", str(root), "--json"]

    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
            cwd=root,
            timeout=int(os.getenv("EVEZ_OPENCLAW_TIMEOUT", "1800")),
            check=False,
        )
    except Exception as exc:
        return {"status": "ERROR", "error": type(exc).__name__}

    return {
        "status": "OK" if result.returncode == 0 else "ERROR",
        "returncode": result.returncode,
        "stdout": result.stdout[-30000:],
        "stderr": result.stderr[-10000:],
    }
