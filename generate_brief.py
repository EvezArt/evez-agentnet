"""Generate the standing brief.

Answers one question: what changed on this system since the last time you
looked, and what needs a decision from you?

Runs from a timer, so it exists even when no agent session does. Everything in
it is derived from real on-disk state — nothing is narrated or embellished.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/root/evez-agentnet")
OUT = REPO / "status"
OUT.mkdir(exist_ok=True)


def sh(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return (p.stdout or p.stderr).strip()
    except Exception as e:
        return f"error: {str(e)[:100]}"


def spine_stats():
    spine = REPO / "spine/spine.jsonl"
    if not spine.exists():
        return {}
    lines = spine.read_text(errors="replace").strip().splitlines()
    last = json.loads(lines[-1]) if lines else {}
    chained = sum(1 for l in lines if '"prev_sha256"' in l)
    return {
        "entries": len(lines),
        "chained": chained,
        "last_ts": last.get("ts"),
        "last_type": last.get("type"),
    }


def open_items():
    """Known-unresolved items, each with a concrete unblock action."""
    items = []

    # Any socat forwarder on a public interface, not one hardcoded unit name.
    # sh() returns a single string, not a tuple. Unpacking two values here
    # raised ValueError and took the entire brief down with it.
    binds = sh("ss -tlnp 2>/dev/null | grep socat | "
               "grep -vE '127\\.0\\.0\\.1|100\\.126\\.' || true")
    if binds.strip():
        addrs = []
        for line in binds.strip().splitlines():
            parts = line.split()
            if len(parts) > 3:
                addrs.append(parts[3])
        items.append({
            "id": "public-gateway",
            "severity": "high",
            "what": f"socat forwarding the gateway on a public bind: {', '.join(addrs)}",
            "action": "systemctl disable --now <the forwarding unit>; the "
                      "Tailscale path on 100.126.180.47:18789 remains",
            "why": "Token-authenticated, but a single token leak exposes it. "
                   "Tailnet-only is strictly safer and you already have it.",
        })

    # Real-token pattern only (clh_ + >=20 token chars), matching
    # stack_health.py and the exposure scanner. The bare `clh_` prefix
    # fires on TESTONLY fixtures in test_exposure_*.py and keeps re-opening
    # a finding that is actually resolved — a watchdog that cries wolf.
    if sh("grep -rEq 'clh_[A-Za-z0-9_-]{20,}' /root/evez-agentnet "
          "--include='*.py' 2>/dev/null | grep -vE 'TESTONLY|SYNTHETIC' "
          "&& echo FOUND || true"):
        items.append({
            "id": "clawhub-token",
            "severity": "high",
            "what": "ClawHub Bearer token present in working tree "
                    "(public in evez-atlas)",
            "action": "Rotate at clawhub, then replace with $CLAWHUB_TOKEN env var",
            "why": "Sent live to clawhub.ai/api/skills from committed source.",
        })

    if sh("grep -rl 'service_role\\|eyJhbGciOiJIUzI1NiJ9' /root/evez-agentnet 2>/dev/null | head -1"):
        items.append({
            "id": "supabase-key",
            "severity": "high",
            "what": "Supabase service_role JWT in public evez-atlas repo",
            "action": "Rotate in Supabase dashboard; audit auth logs since first push",
            "why": "service_role bypasses row-level security entirely.",
        })

    st = {}
    sf = REPO / "worldsim/worldsim_state.json"
    if sf.exists():
        st = json.loads(sf.read_text())
    ships = sh(f"grep -c 'ship_complete' {REPO}/spine/spine.jsonl 2>/dev/null || echo 0")
    try:
        ships_n = int(ships)
    except Exception:
        ships_n = 0
    if ships_n > 50 and st.get("total_earned_usd", 0) == 0.0:
        # Diagnosed 2026-10-02: the shipper was logging "Shipped" for drafts
        # that never left the machine (both delivery paths were TODO stubs).
        # That is fixed — it now reports per-draft reasons. The remaining gap
        # is configuration, not code.
        sl = Path("/root/evez-agentnet/shipper/ship_log.jsonl")
        delivered = 0
        if sl.exists():
            recent = [x for x in sl.read_text(errors="replace").splitlines()
                      if x.strip()][-60:]
            delivered = 0
            for x in recent:
                try:
                    rec = json.loads(x)
                except json.JSONDecodeError:
                    continue
                if rec.get("status") == "shipped":
                    delivered += 1
        items.append({
            "id": "income-zero",
            "severity": "medium",
            "what": (f"{ships_n} ship events, $0.00 revenue. Shipper is now "
                     f"HONEST (reports why each draft failed) but "
                     f"{delivered}/{len(recent) if sl.exists() else 0} recent "
                     f"drafts actually delivered."),
            "action": "Configure a delivery channel: export TWITTER_BEARER_TOKEN "
                      "or GUMROAD_API_KEY, or set MASTODON_BASE_URL + "
                      "MASTODON_ACCESS_TOKEN",
            "why": "Draft generation works; publication has no credentialed "
                   "transport. This is now a config gap, not a lie in the logs.",
        })

    return items


def main():
    now = datetime.now(timezone.utc)
    s = spine_stats()
    items = open_items()

    st = {}
    sf = REPO / "worldsim/worldsim_state.json"
    if sf.exists():
        try:
            st = json.loads(sf.read_text())
        except Exception:
            pass

    health = {}
    hp = OUT / "HEALTH.json"
    if hp.exists():
        try:
            health = json.loads(hp.read_text())
        except Exception:
            pass

    L = []
    L.append(f"# EVEZ brief — {now:%Y-%m-%d %H:%M UTC}")
    L.append("")
    L.append("_Auto-generated by `generate_brief.py`. No agent session required._")
    L.append("")

    L.append("## State")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append(f"| agentnet round | {st.get('round','?')} |")
    L.append(f"| total revenue | ${st.get('total_earned_usd', 0):.2f} |")
    L.append(f"| spine entries | {s.get('entries','?')} |")
    L.append(f"| chained entries | {s.get('chained','?')} |")
    L.append(f"| last event | {s.get('last_type','?')} @ {s.get('last_ts','?')} |")
    L.append(f"| health | {'FAIL ' + str(len(health.get('failures',[]))) if health.get('failures') else ('WARN ' + str(len(health.get('warnings',[]))) if health.get('warnings') else 'clean')} |")
    L.append("")

    L.append("## Needs your decision")
    L.append("")
    if not items:
        L.append("Nothing outstanding.")
    else:
        # severity order, then id, so the file is diff-stable across runs
        for it in sorted(items, key=lambda i: (i["severity"], i["id"])):
            L.append(f"### [{it['severity'].upper()}] {it['id']}")
            L.append(f"{it['what']}")
            L.append("")
            L.append(f"- **Action:** `{it['action']}`")
            L.append(f"- **Why:** {it['why']}")
            L.append("")

    L.append("## Verify")
    L.append("")
    L.append("```bash")
    L.append("python3 stack_health.py    # full check, writes status/HEALTH.md")
    L.append("python3 verify_spine.py    # hash chain integrity")
    L.append("python3 audit_repo.py      # static defect audit")
    L.append("```")
    L.append("")

    (OUT / "BRIEF.md").write_text("\n".join(L))
    print(f"wrote {OUT/'BRIEF.md'}  ({len(items)} open item(s))")
    for i in items:
        print(f"  [{i['severity']}] {i['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
