from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

def run(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=600)
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[-10000:],
        "stderr": result.stderr[-5000:],
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--generated-os", required=True)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    generated = Path(args.generated_os).resolve()

    checks = {
        "boot": run(["python", "boot.py"], generated),
        "adversary": run(["python", str(root / "foundry" / "adversary.py"), "--generated-os", str(generated)], root),
        "replication": run(["python", str(root / "foundry" / "replicate.py"), "--manifest", str(Path(args.manifest).resolve())], root),
    }

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    policy_ok = int(manifest["authority"]["maximum_autonomy"]) <= 5
    checks["authority_policy"] = {"status": "PASS" if policy_ok else "FAIL", "maximum_autonomy": manifest["authority"]["maximum_autonomy"]}

    passed = all(v["status"] == "PASS" for v in checks.values())
    classification = "TESTED" if passed else "UNKNOWN"

    result = {
        "schema": "evez.foundry.evaluation.v1",
        "classification": classification,
        "promotable": False,
        "checks": checks,
        "reason": "Scaffold validation is not capability validation." if passed else "At least one controlled validation failed or was unavailable.",
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
