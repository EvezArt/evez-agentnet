from __future__ import annotations
import argparse
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from runtime.kernel import Kernel

def tamper_test(kernel_root: Path) -> dict:
    spine = kernel_root / "evidence" / "spine.jsonl"
    original = spine.read_text(encoding="utf-8")
    lines = original.splitlines()
    if not lines:
        return {"status": "UNKNOWN", "reason": "no spine events"}
    lines[-1] = lines[-1].replace('"status":"ALLOWED"', '"status":"FORGED"', 1)
    spine.write_text("\n".join(lines) + "\n", encoding="utf-8")
    kernel = Kernel({
        "os_id": "tamper-check",
        "generation": 0,
        "authority": {"maximum_autonomy": 5},
        "agents": [],
    }, kernel_root)
    detected = not kernel.spine.verify()
    spine.write_text(original, encoding="utf-8")
    return {"status": "PASS" if detected else "FAIL", "tamper_detected": detected}

def policy_test(root: Path) -> dict:
    manifest = {
        "os_id": "policy-check",
        "generation": 0,
        "authority": {"maximum_autonomy": 5},
        "agents": ["SCOUT"],
    }
    kernel = Kernel(manifest, root)
    kernel.boot()
    allowed = kernel.request("SCOUT", "OBSERVE")["allowed"]
    denied = kernel.request("SCOUT", "DEPLOY")["allowed"]
    return {"status": "PASS" if allowed and not denied else "FAIL", "observe_allowed": allowed, "deploy_blocked": not denied}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-os", required=True)
    args = ap.parse_args()
    source = Path(args.generated_os).resolve()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        policy = policy_test(root)
        copied = root / "copy"
        import shutil
        shutil.copytree(source, copied)
        tamper = tamper_test(copied)
    result = {
        "schema": "evez.adversarial.result.v1",
        "tests": {"authority_boundary": policy, "spine_tamper_detection": tamper},
        "status": "PASS" if all(x["status"] == "PASS" for x in (policy, tamper)) else "FAIL",
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
