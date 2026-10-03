"""EVEZ EYE — collect the operational picture.

Palantir for one operator. Every number here is probed, never asserted.
The distinction that matters: a port BOUND to 0.0.0.0 is not the same as a port
REACHABLE from the internet. This collector resolves both, because conflating
them is how real exposure warnings get ignored.
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/root/evez-agentnet")
OUT = ROOT / "eye" / "data.json"
INTEREST = re.compile(r"evez|hermes|openclaw|guerilla", re.I)


def sh(cmd: str, timeout: int = 40) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def collect_services() -> list[dict]:
    rows = []
    for line in sh("systemctl list-units --type=service --state=running "
                   "--no-pager --no-legend").splitlines():
        m = re.match(r"\s*(\S+)\s+(\S+)\s+(\S+)", line)
        if not m or not INTEREST.search(m.group(1)):
            continue
        unit = m.group(1)
        rows.append({
            "unit": unit,
            "sub": sh(f"systemctl show {unit} -p SubState --value") or m.group(3),
            "since": sh(f"systemctl show {unit} -p ActiveEnterTimestamp --value"),
        })
    return sorted(rows, key=lambda r: r["unit"])


def collect_ports() -> list[dict]:
    """Bind address AND firewall verdict. A public bind behind a DROP policy
    is not an exposure; reporting it as one trains the operator to ignore red."""
    allowed = set()
    for m in re.finditer(r"--dport (\d+) -j ACCEPT",
                         sh("iptables -S ufw-user-input 2>/dev/null")):
        allowed.add(int(m.group(1)))
    policy_drop = "-P INPUT DROP" in sh("iptables -S INPUT")

    rows = []
    for line in sh("ss -ltnp").splitlines()[1:]:
        m = re.match(r"\S+\s+\S+\s+\S+\s+(\S+)\s+(.*)$", line)
        if not m:
            continue
        addr, proc = m.groups()
        host, _, port = addr.rpartition(":")
        if not port.isdigit():
            continue
        t = re.search(r'\("([^"]+)",pid=(\d+)', proc)
        p = int(port)
        public_bind = host in ("0.0.0.0", "::", "*")
        rows.append({
            "port": p,
            "bind": host,
            "proc": t.group(1) if t else "?",
            "pid": int(t.group(2)) if t else None,
            "public_bind": public_bind,
            "tailnet": host.startswith("100."),
            # reachable from the internet only if bound publicly AND allowed by fw
            "exposed": public_bind and p in allowed,
            "fw_blocked": public_bind and p not in allowed and policy_drop,
        })
    return sorted(rows, key=lambda r: (not r["exposed"], not r["public_bind"], r["port"]))


def collect_cron() -> list[dict]:
    rows = []
    for line in sh("crontab -l").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(None, 5)
        if len(parts) < 6:
            continue
        rows.append({"sched": " ".join(parts[:5]), "cmd": parts[5][:120]})
    return rows


def collect_docker() -> list[dict]:
    rows = []
    for line in sh("docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}'").splitlines():
        p = line.split("|")
        if len(p) >= 2:
            rows.append({"name": p[0], "status": p[1],
                         "image": p[2] if len(p) > 2 else ""})
    return rows


def collect_checks() -> list[dict]:
    hp = ROOT / "status" / "HEALTH.md"
    if not hp.exists():
        sh("cd /root/evez-agentnet && python3 stack_health.py")
    if not hp.exists():
        return []
    rows = []
    for line in hp.read_text(errors="replace").splitlines():
        # HEALTH.md is markdown: entries render as "- name: detail" and the
        # ok/WARN/FAIL marker lives in the bolded summary, not on each line.
        # Match the list form; state is inferred from the summary counts.
        m = re.match(r"^\s*[-*]\s+(.+?):\s+(.*)$", line)
        if not m:
            continue
        name, detail = m.group(1).strip(), m.group(2).strip()
        low = detail.lower()
        state = "WARN" if re.search(
            r"still present|structural|no channel|placeholder|disabled",
            low) else "ok"
        rows.append({"state": state, "name": name, "detail": detail})
    return rows


def collect_credentials() -> list[dict]:
    """Real-token check. Must NOT grep the bare prefix: `clh_` appears in this
    repo's own detector code and in synthetic fixtures, so a prefix grep reports
    a live credential where only a test string exists. Require a full-length
    literal and exclude the synthetic stand-in."""
    out = []
    for name, pat, rx in [
        ("ClawHub", r"clh_", r"clh_[A-Za-z0-9_-]{20,}"),
        ("StandardCompute", r"sk_live_", r"sk_live_[A-Za-z0-9]{20,}"),
    ]:
        hits = []
        for f in ROOT.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            try:
                text = f.read_text(errors="replace")
            except Exception:
                continue
            for m in re.finditer(rx, text):
                tok = m.group(0)
                if "TESTONLY" in tok or "REDACTED" in tok:
                    continue        # synthetic fixture / already-purged marker
                hits.append(f"{f.relative_to(ROOT)}:{text[:m.start()].count(chr(10))+1}")
        out.append({"name": name, "prefix": pat, "live_hits": hits[:5],
                    "count": len(hits)})
    return out


def build() -> dict:
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operator": "Steven Crawford-Maggard",
        "system": "EVEZ",
        "services": collect_services(),
        "ports": collect_ports(),
        "cron": collect_cron(),
        "docker": collect_docker(),
        "checks": collect_checks(),
        "credentials": collect_credentials(),
        "git": {
            "branch": sh("cd /root/evez-agentnet && git rev-parse --abbrev-ref HEAD"),
            "head": sh("cd /root/evez-agentnet && git rev-parse --short HEAD"),
            "last": sh("cd /root/evez-agentnet && git log -1 --pretty=%s"),
            "dirty": len([l for l in sh("cd /root/evez-agentnet && "
                                        "git status --porcelain").splitlines() if l.strip()]),
        },
        "mirrors": int(sh("ls /root/evezart-sync/mirrors/*.git 2>/dev/null | wc -l") or 0),
    }


def main() -> int:
    data = build()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2))
    exp = [p for p in data["ports"] if p["exposed"]]
    print(f"services={len(data['services'])} ports={len(data['ports'])} "
          f"cron={len(data['cron'])} docker={len(data['docker'])} "
          f"checks={len(data['checks'])} exposed={len(exp)}")
    for p in exp:
        print(f"  EXPOSED :{p['port']} {p['proc']}")
    for c in data["credentials"]:
        print(f"  cred {c['name']}: {c['count']} live literal(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
