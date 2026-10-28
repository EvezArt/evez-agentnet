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
import os
from pathlib import Path

REGISTRY = Path("/root/evez-agentnet/forge_output/ATTACKER_REGISTRY.md")
PROMOTE_THRESHOLD = 50   # subnet strikes in 24h to earn standing block
PROMOTE_FAST = 25       # strikes within a 6h burst: walls a range in hours, not days
RAW_DROP_AFTER = 100    # strikes/24h on an already-walled range = kernel-level silence
FIREWALL_WRITES_ENABLED = os.environ.get("EVEZ_ENABLE_FIREWALL_CHANGES", "0").strip() == "1"
WINDOW_H = 24


def sh(argv: list[str]) -> str:
    """Run a fixed executable/argument list without shell interpretation."""
    try:
        result = subprocess.run(argv, shell=False, capture_output=True, text=True, timeout=60)
        return result.stdout if result.returncode == 0 else ""
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
    return "\n".join(line for line in sh(["ufw", "status"]).splitlines() if "DENY" in line)


def ensure_ufw(cidr: str, tag: str) -> bool:
    """Add a DENY rule only when firewall writes are explicitly enabled."""
    try:
        cidr = str(ipaddress.ip_network(cidr, strict=False))
    except ValueError:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", tag):
        return False
    live = ufw_live()
    if cidr in live:
        return False
    if not FIREWALL_WRITES_ENABLED:
        print(f"DRY-RUN: would add UFW deny from {cidr} ({tag})")
        return False
    result = subprocess.run(
        ["ufw", "insert", "1", "deny", "from", cidr, "comment", tag],
        shell=False, capture_output=True, text=True, timeout=60
    )
    return result.returncode == 0


def subnet_strikes(window_h: int) -> dict[str, int]:
    """Live /24 strike counts from ufw.log within the window."""
    import datetime as _dt
    out = subprocess.run(["tail", "-n", "30000", "/var/log/ufw.log"],
                         capture_output=True, text=True, timeout=60).stdout
    now = _dt.datetime.now()
    counts: dict[str, int] = {}
    for line in out.splitlines():
        if "UFW BLOCK" not in line:
            continue
        src = re.search(r"SRC=((?:\d{1,3}\.){3}\d{1,3})", line)
        if not src:
            continue
        tsm = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if tsm:
            try:
                when = _dt.datetime.fromisoformat(tsm.group(1))
                if (now - when).total_seconds() > window_h * 3600:
                    continue
            except ValueError:
                pass
        ip = src.group(1)
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        # NEVER promote local/private space (loopback, docker bridges, LAN)
        # into firewall blocks: hairpinned docker-proxy scans and local
        # services show up with these sources, and blocking them kills the
        # organism's own mesh (2026-10-18: a promoted 127.0.0.1/32 raw drop
        # starved NATS/spine/ollama/redis for 3.5h at boot).
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            continue
        net = ipaddress.ip_network(f"{ip}/24", strict=False)
        counts[str(net)] = counts.get(str(net), 0) + 1
    return counts


def promote_candidates() -> list[tuple[str, int]]:
    """A range earns standing UFW block at 25 strikes/6h (fast) or 50/24h."""
    fast = subnet_strikes(6)
    slow = subnet_strikes(24)
    cands: dict[str, int] = {}
    for net, n in fast.items():
        if n >= PROMOTE_FAST:
            cands[net] = max(cands.get(net, 0), n)
    for net, n in slow.items():
        if n >= PROMOTE_THRESHOLD:
            cands[net] = max(cands.get(net, 0), n)
    return [(c, n) for c, n in sorted(cands.items(), key=lambda x: -x[1])]


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
    # 3. SHARPEN THE TOP: walled ranges still hammering >=100/day get the
    # kernel raw-drop (UFW entry stays as documentation; raw stops the noise
    # from ever reaching the log or the cortex — freeing senses for real signal)
    live = ufw_live()
    day = subnet_strikes(24)
    raw_now = sh(["iptables", "-t", "raw", "-S", "PREROUTING"])
    for net, strikes in sorted(day.items(), key=lambda x: -x[1]):
        if strikes < RAW_DROP_AFTER:
            break
        base = net.split("/")[0]
        if base in live and net not in raw_now:
            try:
                net = str(ipaddress.ip_network(net, strict=False))
            except ValueError:
                continue
            if not FIREWALL_WRITES_ENABLED:
                print(f"DRY-RUN: would add iptables raw DROP for {net} ({strikes} strikes/24h)")
                continue
            r = subprocess.run(
                ["iptables", "-t", "raw", "-I", "PREROUTING", "-s", net, "-j", "DROP"],
                shell=False, capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                actions.append(f"RAW-DROP {net} ({strikes} strikes/24h — firewall writes enabled)")
    for a in actions:
        print(a)
    if not actions:
        print("wall already matches the registry — nothing to roll out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
