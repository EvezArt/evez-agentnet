#!/usr/bin/env python3
"""sealed_bundle.py — the FIX-DIRECTIVE's hard-block, made real.

Law (SECURITY-DIRECTIVE / FIX-DIRECTIVE, 2026-10-12): a manifest is not a
seal. The bundle script MUST regenerate the seal from the bytes on disk,
verify it, and PHYSICALLY ABORT the zip on any mismatch — no window, no
warning-and-continue. The negative test is mandatory and must prove the
abort fires.

Usage:
  sealed_bundle.py build <dir> <out.zip>   # seal + verify + zip, abort on mismatch
  sealed_bundle.py verify <dir>            # verify an existing SHA256SUMS.txt
  sealed_bundle.py negative-test <dir>      # tamper a byte, PROVE the abort fires
"""
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_dir(d: Path) -> dict:
    manifest = {}
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.name not in ("SHA256SUMS.txt",) and not f.name.endswith(".zip"):
            manifest[str(f.relative_to(d))] = digest(f)
    return manifest


def build(d: Path, out: Path) -> int:
    # CHAIN-OF-CUSTODY HARD BLOCK: if a sealed manifest already exists in the
    # directory, the build must verify the CURRENT bytes against the PRIOR
    # seal and ABORT on any mismatch. Regenerating the manifest from whatever
    # bytes happen to be on disk would re-seal tampered files as truth — the
    # exact failure the negative test exposed. A new seal is only legitimate
    # when no prior seal exists (fresh bundle) or after explicit re-seal.
    man_path = d / "SHA256SUMS.txt"
    if man_path.exists():
        rc = verify(d)
        if rc != 0:
            print("ABORT: existing seal fails verification — re-seal refused. "
                  "To force a NEW seal, delete SHA256SUMS.txt deliberately.")
            out.unlink(missing_ok=True)
            return 1
    manifest = seal_dir(d)
    if not manifest:
        print("ABORT: nothing to seal")
        return 1
    man_path.write_text(
        "\n".join(f"{v}  {k}" for k, v in manifest.items()) + "\n")
    # THE HARD BLOCK: regenerate from disk AFTER writing, byte for byte.
    for rel, recorded in manifest.items():
        actual = digest(d / rel)
        if actual != recorded:
            print(f"ABORT: seal mismatch on {rel}: recorded {recorded} != actual {actual}")
            out.unlink(missing_ok=True)  # physically abort the zip
            return 1
    # seal the manifest itself inside the zip
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in manifest:
            zf.write(d / rel, rel)
        zf.write(man_path, "SHA256SUMS.txt")
    # final verification pass on the ZIP's own manifest
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist()) - {"SHA256SUMS.txt"}
        if names != set(manifest):
            print("ABORT: zip contents do not match the sealed manifest")
            out.unlink(missing_ok=True)
            return 1
        for rel, recorded in manifest.items():
            in_zip = hashlib.sha256(zf.read(rel)).hexdigest()
            if in_zip != recorded:
                print(f"ABORT: zip member {rel} hash mismatch")
                out.unlink(missing_ok=True)
                return 1
    print(f"SEALED+VERIFIED {out} — {len(manifest)} files, manifest inside, double-verified")
    return 0


def verify(d: Path) -> int:
    man_path = d / "SHA256SUMS.txt"
    if not man_path.exists():
        print("FAIL: no SHA256SUMS.txt")
        return 1
    fails = 0
    for line in man_path.read_text().splitlines():
        rec, _, rel = line.partition("  ")
        p = d / rel
        if not p.is_file():
            print(f"FAIL: {rel} missing")
            fails += 1
            continue
        if digest(p) != rec:
            print(f"FAIL: {rel} hash mismatch")
            fails += 1
    print("VERIFIED" if not fails else f"{fails} FAILURES")
    return 0 if not fails else 1


def negative_test(d: Path) -> int:
    """Prove the abort fires: seal a copy, tamper a byte, rebuild, REQUIRE failure."""
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td) / "bundle"
        shutil.copytree(d, sandbox, ignore=shutil.ignore_patterns("*.zip", "SHA256SUMS.txt"))
        victim = next((p for p in sorted(sandbox.rglob("*")) if p.is_file()), None)
        if victim is None:
            print("SKIP: nothing to tamper")
            return 1
        # 1. clean build must succeed
        out = Path(td) / "test.zip"
        rc = build(sandbox, out)
        if rc != 0 or not out.exists():
            print("NEGATIVE-TEST FAIL: clean build did not succeed")
            return 1
        # 2. tamper one byte on disk, rebuild, the seal must ABORT
        original = victim.read_bytes()
        victim.write_bytes(original[:-1] + bytes([original[-1] ^ 0xFF]))
        rc = build(sandbox, out)
        if rc == 0 or out.exists():
            print("NEGATIVE-TEST FAIL: tampered bundle did not abort")
            return 1
        print(f"NEGATIVE TEST PASSED: tamper of {victim.name} -> build aborted, zip removed")
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    cmd, target = sys.argv[1], Path(sys.argv[2])
    sys.exit({
        "build": lambda: build(target, Path(sys.argv[3]) if len(sys.argv) > 3 else target / "bundle.zip"),
        "verify": lambda: verify(target),
        "negative-test": lambda: negative_test(target),
    }[cmd]())
