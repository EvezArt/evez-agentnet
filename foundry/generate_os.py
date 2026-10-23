from __future__ import annotations
import argparse
import json
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent / "runtime"

BOOT = '''from __future__ import annotations
import json
from pathlib import Path
from kernel import Kernel
from memory import MemoryStore

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

def main():
    kernel = Kernel(MANIFEST, ROOT)
    print(json.dumps(kernel.boot(), indent=2))
    memory = MemoryStore(ROOT / "memory" / "events.jsonl")
    memory.add("OBSERVATION", "Generated OS boot sequence completed", source="BOOT")
    print(json.dumps(kernel.request("SCOUT", "OBSERVE", purpose="boot smoke test"), indent=2))
    print(json.dumps({
        "state": kernel.state,
        "spine_valid": kernel.spine.verify(),
        "memory_items": len(memory.search("boot", limit=20)),
    }, indent=2))

if __name__ == "__main__":
    main()
'''

def main():
    ap = argparse.ArgumentParser(description="Generate a minimal bootable EVEZ OS candidate.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).resolve().read_text(encoding="utf-8"))
    required = ["os_id", "generation", "objective", "kernel", "agents", "authority", "evidence"]
    missing = [key for key in required if key not in manifest]
    if missing:
        raise SystemExit("manifest missing: " + ", ".join(missing))
    if int(manifest["authority"]["maximum_autonomy"]) > 5:
        raise SystemExit("generator refuses candidates above A5")

    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output: {out}")
    out.mkdir(parents=True, exist_ok=True)

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for module in ("kernel.py", "memory.py"):
        (out / module).write_text(
            (RUNTIME / module).read_text(encoding="utf-8"), encoding="utf-8"
        )

    (out / "boot.py").write_text(BOOT, encoding="utf-8")
    (out / "README.md").write_text(
        "# " + manifest["os_id"] + "\n\n"
        + "Objective: " + manifest["objective"] + "\n\n"
        + "Status: PROPOSED. Generated scaffold; capabilities require independent testing and replication.\n\n"
        + "Boot: python boot.py\n"
        + "Evidence: evidence/spine.jsonl\n"
        + "Memory: memory/events.jsonl\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "out": str(out),
        "os_id": manifest["os_id"],
        "generation": manifest["generation"],
        "status": "GENERATED_PROPOSED",
    }, indent=2))

if __name__ == "__main__":
    main()
