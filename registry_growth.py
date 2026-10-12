#!/usr/bin/env python3
"""registry_growth.py — the attacker registry grows like a living organ.

The enemy receptor sees ~880 genuinely-new sources a day; the registry was
a static 6-IP narrative. This folds confirmed contacts into an append-only
CONTACT LEDGER section: every entry hash-stamped, deduped, with the
first-seen date and strike count. The narrative operators stay untouched —
history is append-only for the registry too.

Law: this file records CONTACT, not attribution. A source IP in the ledger
is evidence of firewall contact only. "A network indicator is not an
attribution" — the registry's own doctrine.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

HOME = Path("/root/evez-agentnet")
REGISTRY = HOME / "forge_output" / "ATTACKER_REGISTRY.md"
LEDGER_SECTION = "## CONTACT LEDGER (auto-appended)"
WINDOW_H = 24


def top_blockers(window_h: int = WINDOW_H, limit: int = 25) -> list[tuple[str, int]]:
    """Top sources by UFW blocks in the last window, from the live log."""
    out = subprocess.run(["tail", "-n", "30000", "/var/log/ufw.log"],
                          capture_output=True, text=True, timeout=60).stdout
    now = dt.datetime.now()
    counts: dict[str, int] = {}
    for line in out.splitlines():
        if "UFW BLOCK" not in line:
            continue
        tsm = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        src = re.search(r"SRC=((?:\d{1,3}\.){3}\d{1,3})", line)
        if not src:
            continue
        if tsm:
            try:
                when = dt.datetime.fromisoformat(tsm.group(1))
                if (now - when).total_seconds() > window_h * 3600:
                    continue
            except ValueError:
                pass
        ip = src.group(1)
        if ip.startswith(("10.", "172.16.", "192.168.")):
            continue
        counts[ip] = counts.get(ip, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:limit]


def existing_ips() -> set[str]:
    """IPs already in the registry — including every host inside any CIDR."""
    import ipaddress
    t = REGISTRY.read_text(errors="replace")
    known: set[str] = set()
    for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b", t):
        tok = m.group(0)
        if "/" in tok:
            try:
                net = ipaddress.ip_network(tok, strict=False)
                known.update(str(h) for h in net.hosts())
            except ValueError:
                continue
        else:
            known.add(tok)
    return known


def main() -> int:
    if not REGISTRY.exists():
        print("registry missing")
        return 1
    known = existing_ips()
    fresh = [(ip, c) for ip, c in top_blockers() if ip not in known]
    if not fresh:
        print("no new contacts to record")
        return 0
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for ip, c in fresh:
        stamp = hashlib.sha256(f"{ip}:{today}".encode()).hexdigest()[:12]
        rows.append(f"| {ip} | {c} | {today} | {stamp} | contact only — no attribution |")
    block = "\n".join([f"\n### {today}", "", "| Source | Strikes (24h) | First seen | Stamp | Note |",
                       "|---|---|---|---|---|"] + rows)
    t = REGISTRY.read_text()
    if LEDGER_SECTION not in t:
        t = t.rstrip() + "\n\n" + LEDGER_SECTION + "\n" + block + "\n"
    else:
        # append under the ledger section (before any later section, else at end)
        t = t.rstrip() + "\n" + block + "\n"
    REGISTRY.write_text(t)
    print(f"registry grew: +{len(fresh)} contacts")
    for ip, c in fresh[:8]:
        print(f"  {ip}: {c} strikes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
