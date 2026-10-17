from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def tree_digest(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "evidence" not in path.parts:
            rel = path.relative_to(root).as_posix()
            entries.append((rel, file_digest(path)))
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--generator", default=str(Path(__file__).resolve().parent / "generate_os.py"))
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a = root / "a"
        b = root / "b"
        commands = []
        for out in (a, b):
            command = ["python", args.generator, "--manifest", args.manifest, "--out", str(out)]
            result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=300)
            commands.append({
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            })
            if result.returncode != 0:
                print(json.dumps({"status": "FAIL", "commands": commands}, indent=2))
                return
        first = tree_digest(a)
        second = tree_digest(b)
        result = {
            "schema": "evez.replication.result.v1",
            "status": "PASS" if first == second else "FAIL",
            "digest_a": first,
            "digest_b": second,
            "commands": commands,
            "scope": "generated scaffold excluding mutable evidence",
        }
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
