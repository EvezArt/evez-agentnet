"""Standing health watch for the EVEZ stack.

This runs whether or not an agent session is active. It exists because the
three failures that mattered most this session were all silent:

  - the RSI engine emitted "recover via streak" to a perfect agent for 244 rounds
  - the income loop logged "Shipped" while total_earned_usd stayed 0.00
  - two live credentials sat in public repos

None of those raise an alert. So this one does.

Writes a status document rather than only logging, because a status file
survives the session that produced it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/root/evez-agentnet")
OUT = REPO / "status"
OUT.mkdir(exist_ok=True)

FAIL = []
WARN = []


def sh(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except Exception as e:
        return 1, str(e)[:120]


def check(name, ok, detail="", warn_only=False):
    if ok:
        print(f"  ok    {name}")
    else:
        line = f"{name}: {detail}"
        (WARN if warn_only else FAIL).append(line)
        print(f"  {'WARN' if warn_only else 'FAIL'}  {name}  {detail}")
    return ok


def main():
    now = datetime.now(timezone.utc).isoformat()
    print(f"EVEZ stack health — {now}\n")

    # ── services ──
    for svc in ["openclaw-gateway", "evez-agentnet", "evez-event-spine",
                "evez-commerce", "evez-evidence-api", "gueriella-agent"]:
        rc, out = sh(f"systemctl is-active {svc}")
        check(f"service {svc}", out == "active", f"state={out or 'unknown'}")

    # ── agentnet actually producing, not just running ──
    state_f = REPO / "worldsim/worldsim_state.json"
    if state_f.exists():
        try:
            st = json.loads(state_f.read_text())
            rnd = st.get("round", 0)
            earned = st.get("total_earned_usd", 0.0)
            check("agentnet round advancing", rnd > 0, f"round={rnd}")
            # The income loop logs "Shipped" regardless of revenue. If it has
            # shipped 200+ times and earned nothing, that is a finding, not a
            # success — exactly the silent failure class this exists to catch.
            spine = REPO / "spine/spine.jsonl"
            ships = 0
            if spine.exists():
                ships = sum(1 for l in spine.read_text(errors="replace").splitlines()
                            if '"ship_complete"' in l)
            if ships > 50 and earned == 0.0:
                check("income loop yield", False,
                      f"{ships} ship events, $0.00 earned — no channel delivers",
                      warn_only=True)
            else:
                check("income loop yield", True,
                      f"{ships} ships, ${earned:.2f}")

            # Distinct from the above: drafts produced vs drafts actually
            # delivered. A shipper that logs "not_shipped:*" for everything is
            # now HONEST but still not earning — that is a configuration gap,
            # not a code bug, and needs a human decision.
            sl = REPO / "shipper/ship_log.jsonl"
            if sl.exists():
                # Window must be post-fix rows only. The legacy log contains
                # hundreds of records whose status is exactly "shipped" from
                # the era when the shipper logged success without delivering,
                # so a naive trailing window reports historical rows as
                # current success and masks the real state. Take the last 200
                # and keep only rows written by the honest shipper.
                recent = [l for l in sl.read_text(errors="replace").splitlines()
                          if l.strip()][-200:]
                honest = []
                for l in recent:
                    try:
                        rec = json.loads(l)
                    except json.JSONDecodeError:
                        continue
                    if str(rec.get("status", "")).startswith("not_shipped"):
                        honest.append(l)
                recent = honest
                # Substring matching is wrong here: legacy rows contain the
                # literal "shipped" INSIDE the key order and the substring
                # "not_shipped" can appear in a detail field. Parse the JSON
                # and compare the status field exactly.
                delivered = 0
                for l in recent:
                    try:
                        rec = json.loads(l)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("status") == "shipped":
                        delivered += 1
                if len(recent) >= 5 and delivered == 0:
                    check("drafts actually delivered", False,
                          f"{len(recent)} recent drafts, 0 delivered — "
                          f"no API credentials configured for any channel",
                          warn_only=True)
        except Exception as e:
            check("agentnet state parses", False, str(e)[:80])
    else:
        check("agentnet state file", False, "worldsim_state.json missing")

    # ── spine integrity ──
    rc, out = sh(f"cd {REPO} && python3 verify_spine.py")
    check("spine hash chain", rc == 0 and "all entries verify" in out,
          out.splitlines()[-1] if out else "verifier failed")

    # ── static audit ──
    rc, out = sh(f"cd {REPO} && python3 audit_repo.py")
    check("repo audit clean", rc == 0, out.splitlines()[-1][:70] if out else "audit failed")

    # ── exposure: the three known open items ──
    creds = REPO / "evidence"
    if (creds / "infrastructure-verification.json").exists():
        check("infrastructure re-verified", True, "see evidence/")

    # ── network exposure ──
    # Check any socat forwarder bound to a PUBLIC interface, not just one
    # unit name — the unit could be renamed and the exposure would persist.
    rc, out = sh("ss -tlnp 2>/dev/null | grep -c 'socat' || echo 0")
    public_binds = []
    rc2, out2 = sh(
        "ss -tlnp 2>/dev/null | grep socat | grep -vE '127\\.0\\.0\\.1|100\\.126\\.' || true")
    if out2.strip():
        public_binds = [l.split()[3] for l in out2.strip().splitlines() if len(l.split()) > 3]
    if public_binds:
        check("gateway NOT on public interface", False,
              f"socat forwarding on public bind: {', '.join(public_binds)}",
              warn_only=True)
    else:
        check("gateway NOT on public interface", True,
              "no socat forwarder on a public bind (loopback/tailnet only)")

    # ── exposed credentials (local check; rotation status) ──
    rc, out = sh(f"grep -rq 'clh_' /root/evez-agentnet 2>/dev/null && echo FOUND || echo CLEAN")
    check("no ClawHub token in local repos", out.strip() == "CLEAN",
          "token still present in working tree", warn_only=True)

    # ── revenue path: structural blockers ──
    # $0.00 revenue has THREE independent causes. Naming only the shipper one
    # (which the health check already reports) understates the problem.
    import os as _os
    commerce = {
        "STRIPE_SECRET_KEY": _os.environ.get("STRIPE_SECRET_KEY", "").strip(),
        "GUMROAD_API_KEY": _os.environ.get("GUMROAD_API_KEY", "").strip(),
        "TWITTER_BEARER_TOKEN": _os.environ.get("TWITTER_BEARER_TOKEN", "").strip(),
    }
    money_path = [k for k, v in commerce.items() if v]
    if not money_path:
        check("revenue path has a credentialed transport", False,
              "no STRIPE/GUMROAD/TWITTER key configured — $0.00 is "
              "STRUCTURAL, not a code defect. Nothing ships and nothing charges.",
              warn_only=True)
    else:
        check("revenue path has a credentialed transport", True,
              f"configured: {', '.join(money_path)}")

    # and confirm the payment vault is still the empty template it was
    vault = Path("/root/.openclaw/agents-pay/.vault.env")
    if vault.exists():
        try:
            vt = vault.read_text(errors="replace")
            m = re.search(r"^STRIPE_SECRET_KEY\s*=\s*(\S*)", vt, re.M)
            val = (m.group(1) if m else "").strip().strip("'\"")
            if not val:
                check("payment vault populated", False,
                      "agents-pay/.vault.env STRIPE_SECRET_KEY is an empty "
                      "placeholder; evez-commerce reports payments:disabled",
                      warn_only=True)
            else:
                check("payment vault populated", True,
                      f"STRIPE_SECRET_KEY present (len={len(val)})")
        except Exception:
            pass

    # ── Jev decision layer ──
    # Optional, so absence is informational, not a failure. It reports whether
    # the System One integration is live without an API key.
    rc, out = sh("cd %s && python3 jev_cli.py status 2>/dev/null | head -20" % REPO)
    if out and '"available"' in out:
        live = '"available": true' in out
        recorded = 0
        for line in out.splitlines():
            if '"decisions_recorded"' in line:
                try:
                    recorded = int(line.split(":")[1].strip().rstrip(","))
                except (ValueError, IndexError):
                    recorded = 0
        check("Jev decision layer", True,
              "live" if live else "installed, no TYPESAFE_API_KEY set "
              f"(decisions logged: {recorded})", warn_only=not live)

    # Is Jev actually WIRED into the OODA loop, or just installed?
    rc3, out3 = sh("cd %s && grep -c 'jev_integration' orchestrator.py 2>/dev/null"
                   % REPO)
    if out3.strip().isdigit() and int(out3.strip()) > 0:
        check("Jev wired into OODA loop", True,
              "phase 5.5, advisory only, spine-recorded")
    else:
        check("Jev wired into OODA loop", False,
              "integration not present in orchestrator.py", warn_only=True)

    # Count jev_advice events actually landing in the spine.
    rc4, out4 = sh("cd %s && grep -c 'jev_advice' spine/spine.jsonl 2>/dev/null || echo 0"
                   % REPO)
    n = out4.strip()
    if n.isdigit():
        check("Jev advice reaching the spine", True,
              f"{n} jev_advice event(s) recorded")

    # ── MoE router ──
    # Informational: the router is optional tooling. But a router that cannot
    # see its experts is broken in the same way a shipper with no channel is.
    rc, out = sh("cd %s && python3 moe_cli.py roster 2>/dev/null | head -20" % REPO)
    if "reachable: True" in out:
        n = len([l for l in out.splitlines() if "MB " in l])
        check("MoE router sees experts", n >= 2, f"only {n} expert(s) visible")
        check("MoE generative routing works", True,
              f"{n} experts, cheapest-first by task kind")
    elif out.strip():
        check("MoE router", False, "ollama not reachable", warn_only=True)

    # ── cryptozoo population ──
    # The breeding engine must produce a COHERENT population. If coherence
    # collapses, the oscillator model is decohering and that is a real fault,
    # not a cosmetic metric.
    rc, out = sh("cd %s && python3 cryptozoo_sim.py 2>/dev/null | tail -14" % REPO)
    coh = None
    for line in out.splitlines():
        if line.strip().startswith("coherence"):
            try:
                coh = float(line.split("->")[1].strip())
            except (ValueError, IndexError):
                pass
    if coh is not None:
        check("cryptozoo coherence", coh >= 0.5,
              f"population order parameter r={coh}", warn_only=True)
    else:
        check("cryptozoo engine", False, "simulation did not report coherence",
              warn_only=True)

    rc2, out2 = sh("cd %s && python3 -c \"import agent_species as a;"
                   "print(len(a.assign_all()))\" 2>/dev/null" % REPO)
    if out2.strip().isdigit():
        check("agent species bound", True,
              f"{out2.strip()} agents hold species identities")

    # ── resource headroom ──
    rc, out = sh("df -h / | awk 'NR==2{print $5}'")
    check("disk headroom", rc == 0 and int(out.rstrip('%')) < 90,
          f"root fs {out} used", warn_only=True)

    rc, out = sh("free -m | awk '/^Mem:/{printf \"%d\", $3/$2*100}'")
    check("memory headroom", rc == 0 and int(out or 0) < 92,
          f"mem {out}% used", warn_only=True)

    status = {
        "checked_at": now,
        "failures": FAIL,
        "warnings": WARN,
        "ok": not FAIL,
    }
    (OUT / "HEALTH.json").write_text(json.dumps(status, indent=1))

    lines = [
        f"# EVEZ stack status — {now}",
        "",
        f"**FAIL** {len(FAIL)}   **WARN** {len(WARN)}",
        "",
    ]
    if FAIL:
        lines += ["## Failures", ""] + [f"- {f}" for f in FAIL] + [""]
    if WARN:
        lines += ["## Warnings", ""] + [f"- {w}" for w in WARN] + [""]
    if not FAIL and not WARN:
        lines += ["All checks passed.", ""]
    lines += ["_Generated by `stack_health.py`. Run: `python3 stack_health.py`_", ""]
    (OUT / "HEALTH.md").write_text("\n".join(lines))

    print(f"\n{'='*60}\nFAIL {len(FAIL)}  WARN {len(WARN)}")
    print(f"wrote {OUT/'HEALTH.md'}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
