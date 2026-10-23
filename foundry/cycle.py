from __future__ import annotations
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from bridge.hermes import invoke as invoke_hermes
from bridge.openclaw import invoke as invoke_openclaw

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def run_local(args: list[str], cwd: Path) -> dict:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False, timeout=900)
    return {
        "status": "OK" if result.returncode == 0 else "ERROR",
        "returncode": result.returncode,
        "stdout": result.stdout[-20000:],
        "stderr": result.stderr[-10000:],
    }

def main():
    ap = argparse.ArgumentParser(description="Run one bounded EVEZ Foundry assembly cycle.")
    ap.add_argument("--objective", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--work", default="data/foundry-cycle")
    args = ap.parse_args()

    work = (REPO_ROOT / args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)

    compile_out = work / "candidate.json"
    generated = work / "generated-os"

    compile_result = run_local([
        "python", str(ROOT / "assemble.py"),
        args.objective,
        "--graph", args.inventory,
        "--out", str(compile_out),
    ], REPO_ROOT)
    if compile_result["status"] != "OK":
        raise SystemExit(json.dumps(compile_result, indent=2))

    generate_result = run_local([
        "python", str(ROOT / "generate_os.py"),
        "--manifest", str(compile_out),
        "--out", str(generated),
    ], REPO_ROOT)
    if generate_result["status"] != "OK":
        raise SystemExit(json.dumps(generate_result, indent=2))

    boot_result = run_local(["python", "boot.py"], generated)

    packet = {
        "observed_at": now(),
        "objective": args.objective,
        "candidate": str(compile_out),
        "generated_os": str(generated),
        "compile": compile_result,
        "generate": generate_result,
        "boot": boot_result,
    }

    hermes_result = invoke_hermes(packet, REPO_ROOT)
    packet["hermes"] = {
        "status": hermes_result.get("status"),
        "output": hermes_result.get("output", ""),
        "stderr": hermes_result.get("stderr", ""),
    }

    task_file = work / "openclaw_task.json"
    task_file.write_text(json.dumps({
        "schema": "evez.foundry.task.v1",
        "authority_max": 5,
        "objective": args.objective,
        "candidate": str(compile_out),
        "generated_os": str(generated),
        "instructions": [
            "Inspect candidate and boot evidence.",
            "Work locally and in isolation.",
            "Propose repairs for failures; do not deploy or publish.",
            "Preserve contradictions instead of hiding them.",
        ],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    openclaw_result = invoke_openclaw(task_file, REPO_ROOT)
    packet["openclaw"] = {
        "status": openclaw_result.get("status"),
        "stdout": openclaw_result.get("stdout", ""),
        "stderr": openclaw_result.get("stderr", ""),
    }

    (work / "cycle-result.json").write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "objective": args.objective,
        "compile": compile_result["status"],
        "generate": generate_result["status"],
        "boot": boot_result["status"],
        "hermes": hermes_result["status"],
        "openclaw": openclaw_result["status"],
        "result": str(work / "cycle-result.json"),
    }, indent=2))

if __name__ == "__main__":
    main()
