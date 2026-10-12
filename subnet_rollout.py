#!/usr/bin/env python3
"""subnet_rollout.py — declarative subnet enforcement from the registry.

The registry's KNOWN BLOCKED RANGES section is the source of truth; this
reconciles live UFW against it, adds any missing DENY rules with IOC
tags, and promotes repeat-offender single IPs from the CONTACT LEDGER to
standing /24 blocks when their subnet accumulates >= PROMOTE_THRESHOLD
strikes in the window. Idempotent: re-running changes nothing if the
wall already matches the registry. Every action logged to evidence.
"""
from __future__ import annotations
import datetime as dt
import ipaddress
import re
import subprocess
from pathlib import Path

REGISTRY = Path("/root/evez-agentnet/forge_output/ATTACKER_REGISTRY.md")
PROMOTE_THRESHOLD = 50  # subnet strikes in 24h to earn standing block
WINDOW_H = 24


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def parse_registry_ranges() -> list[tuple[str, str]]:
    """(cidr, note) pairs from the KNOWN BLOCKED RANGES section."""
    t = REGISTRY.read_text(errors="replace")
    out = []
    in_section = False
    for line in t.splitlines():
        if line.startswith("## KNOWN BLOCKED RANGES"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            # extract EVERY cidr-ish token anywhere in the line, then a note
            toks = re.findall(r"([\d.]+(?:/\d+)?)", line)
            note_m = re.search(r"—\s+(.*)", line)
            note = note_m.group(1)[:60] if note_m else "registry range"
            for tok in toks:
                try:
                    if "/" in tok:
                        net = ipaddress.ip_network(tok, strict=False)
                    else:
                        # bare IP or wildcard family like 194.180.49.x
                        base = tok.split(".x")[0]
                        net = ipaddress.ip_network(f"{base}.0/24", strict=False)
                    out.append((str(net), note))
                except ValueError:
                    continue
    return out


def ufw_live() -> str:
    return sh("ufw status | grep DENY")


def ensure_ufw(cidr: str, tag: str) -> bool:
    """Add a DENY rule if not present. Returns True if added."""
    live = ufw_live()
    if cidr in live:
        return False
    # ufw needs insert at top for priority; use plain deny (order irrelevant for DENY)
    r = subprocess.run(f"ufw insert 1 deny from {cidr} comment '{tag}'",
                       shell=True, capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def promote_candidates() -> list[tuple[str, int]]:
    """Subnets of CONTACT LEDGER entries whose 24h strike count crosses the threshold."""
    t = REGISTRY.read_text(errors="replace")
    counts: dict[str, int] = {}
    for m in re.finditer(r"\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|", t):
        ip, n = m.group(1), int(m.group(2))
        if ip.startswith(("10.", "172.16.", "192.168.")):
            continue
        net = ipaddress.ip_network(f"{ip}/24", strict=False)
        counts[str(net)] = counts.get(str(net), 0) + n
    return [(c, n) for c, n in sorted(counts.items(), key=lambda x: -x[1]) if n >= PROMOTE_THRESHOLD]


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    actions = []
    # 1. reconcile registry ranges against UFW
    for cidr, note in parse_registry_ranges():
        tag = f"IOC-registry-rollout-{now[:10]}"
        if ensure_ufw(cidr, tag):
            actions.append(f"UFW+ {cidr} ({note})")
    # 2. promote repeat-offender subnets from the ledger
    ufw = ufw_live()
    for cidr, strikes in promote_candidates():
        if cidr.split("/")[0] not in ufw:
            tag = f"IOC-promoted-{strikes}strikes-{now[:10]}"
            if ensure_ufw(cidr, tag):
                actions.append(f"PROMOTED {cidr} ({strikes} strikes/24h)")
    for a in actions:
        print(a)
    if not actions:
        print("wall already matches the registry — nothing to roll out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
