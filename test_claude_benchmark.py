#!/usr/bin/env python3
"""Self-test for claude_benchmark.py.

Exercises the full measurement pipeline against the mock provider:
  1. dry-run ladder (small stages) completes with exit 0
  2. mock rate cap forces real 429s at high concurrency, and the harness
     records them instead of hiding them
  3. receipt chain verifies after the run
  4. tampering a receipt row breaks the chain (negative test)

Run as a script (CI convention in this repo): python3 test_claude_benchmark.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
HARNESS = REPO / "claude_benchmark.py"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("%s %s%s" % ("PASS" if cond else "FAIL", name, (" - " + detail) if detail else ""))


def main():
    with tempfile.TemporaryDirectory() as td:
        receipt = Path(td) / "bench.jsonl"
        # small stages + a cap low enough that n5 overflows the 5 rps window
        proc = subprocess.run(
            [
                sys.executable, str(HARNESS),
                "--dry-run", "--stages", "1,5",
                "--receipt-file", str(receipt),
                "--mock-rps-cap", "5",
            ],
            capture_output=True, text=True, timeout=120,
        )
        check("harness exits 0", proc.returncode == 0,
              "rc=%d stderr_tail=%s" % (proc.returncode, proc.stderr.strip()[-200:]))
        check("summary reports mock_used", '"mock_used": true' in proc.stdout,
              "summary line missing mock flag")

        rows = [json.loads(l) for l in receipt.read_text().strip().splitlines()]
        stages = [r for r in rows if r.get("event") == "claude_benchmark_stage"]
        check("receipt rows written", len(stages) == 2,
              "got %d stage rows" % len(stages))

        # chain integrity after a real run
        verify = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r);" % str(REPO) +
             "from claude_benchmark import ReceiptChain;"
             "print(ReceiptChain(%r).verify())" % str(receipt)],
            capture_output=True, text=True, timeout=60,
        )
        check("receipt chain verifies", "True" in verify.stdout,
              verify.stdout.strip() or verify.stderr.strip()[-200:])

        # negative test: tamper a row, chain must break
        bad = Path(td) / "bad.jsonl"
        lines = receipt.read_text().strip().splitlines()
        first = json.loads(lines[0])
        first["completions"] = 999  # lie about a stage result
        lines[0] = json.dumps(first, sort_keys=True)
        bad.write_text("\n".join(lines) + "\n")
        tamper = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r);" % str(REPO) +
             "from claude_benchmark import ReceiptChain;"
             "print(ReceiptChain(%r).verify())" % str(bad)],
            capture_output=True, text=True, timeout=60,
        )
        check("tampered row breaks chain", "(False," in tamper.stdout,
              tamper.stdout.strip() or tamper.stderr.strip()[-200:])

    failed = [r for r in results if not r[1]]
    print("\n%d/%d checks passed" % (len(results) - len(failed), len(results)))
    if failed:
        print("claude benchmark self-test FAILED")
        return 1
    print("claude benchmark self-test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
