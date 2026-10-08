"""Prove the public-interface check is state-agnostic.

Original check tested one hardcoded unit name. A rename would have hidden the
exposure. This asserts the check keys on actual socket binds, by binding a
socat forwarder on a public interface and confirming the check fires.
"""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sh", "/root/evez-agentnet/stack_health.py")
SH = importlib.util.module_from_spec(spec)
sys.modules["sh"] = SH
spec.loader.exec_module(SH)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


PUBLIC_IP = "80.241.209.34"


def public_socat_binds():
    _, out = SH.sh(
        "ss -tlnp 2>/dev/null | grep socat | "
        "grep -vE '127\\.0\\.0\\.1|100\\.126\\.' || true")
    return [l.split()[3] for l in out.strip().splitlines() if len(l.split()) > 3]


print("baseline: gateway must NOT be on a public interface")
binds = public_socat_binds()
print(f"  public socat binds: {binds or 'none'}")
expect("no public forwarder currently bound", not binds, str(binds))

print("\nplant a forwarder on the public IP and confirm detection")
# Use an ephemeral port so the real gateway is untouched.
PORT = "18999"
p = subprocess.Popen(
    ["socat", f"TCP-LISTEN:{PORT},bind={PUBLIC_IP},reuseaddr,fork",
     "TCP:127.0.0.1:18789"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2.5)
try:
    binds = public_socat_binds()
    print(f"  public socat binds now: {binds}")
    expect("planted forwarder is detected", any(PUBLIC_IP in b for b in binds),
           str(binds))

    # the brief must also flag it
    import generate_brief as GB
    items = GB.open_items()
    ids = [i["id"] for i in items]
    expect("brief raises public-gateway", "public-gateway" in ids, str(ids))
    pg = next((i for i in items if i["id"] == "public-gateway"), None)
    if pg:
        print(f"    detail: {pg['what'][:78]}")
        expect("brief names the offending address",
               PUBLIC_IP in pg["what"], pg["what"])

    # and the health check must WARN
    SH.FAIL.clear(); SH.WARN.clear()
    SH.check("gateway NOT on public interface", False,
             f"socat forwarding on public bind: {', '.join(binds)}",
             warn_only=True)
    expect("health records a WARN, not a FAIL",
           len(SH.WARN) == 1 and len(SH.FAIL) == 0,
           f"F={SH.FAIL} W={SH.WARN}")
finally:
    p.terminate()
    try:
        p.wait(timeout=5)
    except Exception:
        p.kill()
    time.sleep(1.5)

print("\nafter teardown")
binds = public_socat_binds()
expect("back to no public binds", not binds, str(binds))

import generate_brief as GB
ids = [i["id"] for i in GB.open_items()]
expect("brief no longer raises public-gateway", "public-gateway" not in ids,
       str(ids))

# the real gateway must still be reachable the intended ways
rc, out = SH.sh("curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/")
expect("local gateway still serving", out.strip() == "200", out.strip())
rc, out = SH.sh("curl -s -m 5 -o /dev/null -w '%{http_code}' http://100.126.180.47:18790/health")
expect("tailnet gateway still serving", out.strip() == "200", out.strip())

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
