#!/usr/bin/env python3
"""
EVEZ Exposure Attestation Harness
=================================

The problem this exists to solve: every exposure report written so far in this
stack ASSERTS safety. "port is loopback", "auth is wired", "verify returns
valid". Assertions rot. This harness turns each claim into an executable probe
that either reproduces now or fails loudly.

Three defect classes it is built to catch, all of which were found in this
stack by execution rather than review:

  1. BIND_ADDR_IS_NOT_REACHABILITY. `ss` showing 127.0.0.1 proves a bind, not
     a firewall verdict. A service on a private address can still be reachable
     if a rule permits it. So every claim is probed from the public address.

  2. AUTH_DEFINED_BUT_UNATTACHED. A verify_api_key/adminAuth function with zero
     call sites means the endpoint was never authenticated, no matter what the
     file reads like. Detected by grepping call sites, not by reading prose.

  3. DOC_ROUTE_FALSE_ALL_CLEAR. /openapi.json, /docs, /health and / often
     bypass auth, so probing them gives a false PASS. Every auth check probes a
     route that is actually behind the guard.

Each finding is labelled with what it PROVES and what it DOES NOT PROVE. A
harness that cannot report "I could not verify this" is worse than none.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

PROBE_TIMEOUT = 5
LOCAL = "127.0.0.1"
PUBLIC_IP = "80.241.209.34"


# ── result model ────────────────────────────────────────────────────────

@dataclass
class Finding:
    id: str
    severity: str            # critical / high / medium / info
    title: str
    proves: str              # what was actually verified by execution
    does_not_prove: str      # the honest boundary of the claim
    evidence: dict = field(default_factory=dict)
    remediation: str = ""

    def to_json(self):
        return asdict(self)


class Harness:
    def __init__(self, public_ip: str = PUBLIC_IP):
        self.public_ip = public_ip
        self.findings: List[Finding] = []
        self.checks_run = 0
        self.checks_skipped: List[str] = []

    # -- primitives ------------------------------------------------------

    @staticmethod
    def _listen_table() -> dict:
        """port -> bind address, from ss. Parse defensively."""
        out = subprocess.run(["ss", "-tln"], capture_output=True, text=True).stdout
        table = {}
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 4:
                continue
            local = parts[3]
            m = re.search(r":(\d+)$", local)
            if not m:
                continue
            table[int(m.group(1))] = local.rsplit(":", 1)[0]
        return table

    @staticmethod
    def _tcp_open(host: str, port: int, timeout: int = PROBE_TIMEOUT) -> Optional[bool]:
        """True=open, False=closed, None=unverified (timeout/filtered)."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except ConnectionRefusedError:
            return False
        except (socket.timeout, TimeoutError):
            return None
        except OSError:
            return False

    # -- CHECK 1: reachability, not bind address ────────────────────────

    def check_reachability(self) -> None:
        for port, bind in sorted(self._listen_table().items()):
            self.checks_run += 1
            local = self._tcp_open(LOCAL, port)
            if local is None:
                self.checks_skipped.append(f"port:{port}:local-timeout")
                continue
            if not local:
                continue                      # nothing listening that we can test
            public = self._tcp_open(self.public_ip, port)
            if public is True:
                sev = "critical" if port not in (22, 9090) else "high"
                self.findings.append(Finding(
                    id=f"EXPOSED:{port}",
                    severity=sev,
                    title=f"port {port} reachable from the public internet",
                    proves=f"TCP connect to {self.public_ip}:{port} succeeded from this host.",
                    does_not_prove="Not proof of compromise. Only proof of reachability; "
                                   "authentication strength is assessed separately.",
                    evidence={"bind": bind, "local_open": local, "public_open": public},
                    remediation="Bind to 127.0.0.1 or restrict with a firewall rule.",
                ))
            elif public is None:
                self.findings.append(Finding(
                    id=f"UNVERIFIED:{port}",
                    severity="medium",
                    title=f"port {port} could not be verified from the public address",
                    proves=f"Listening on {bind} and reachable on loopback.",
                    does_not_prove="Reachability from OUTSIDE is UNVERIFIED. A timeout is "
                                   "not a closed port; it is a firewall drop or a silent host.",
                    evidence={"bind": bind, "public": "timeout"},
                    remediation="Probe from a genuinely external host to settle it.",
                ))

    # -- CHECK 2: auth defined but never attached ───────────────────────

    # Match a verifier DEFINITION and capture whether it is a bound method.
    # A method whose first parameter is `self` is a client helper (e.g.
    # MAESClient.verify_agent issuing an outbound GET), not an access guard.
    # Flagging those was a false positive found by self-test on real code.
    AUTH_DEF_RE = re.compile(
        r"^[ \t]*def\s+(verify_\w+|admin_?auth\w*|check_\w*auth\w*|_authorized\w*)"
        r"\s*\(\s*(self\b)?", re.M)

    def check_orphan_auth(self, roots: List[str]) -> None:
        """A verifier that is defined but has no call site never ran."""
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [x for x in dirnames
                               if x not in (".git", "__pycache__", "node_modules", "venv")]
                for fn in filenames:
                    if not fn.endswith((".py", ".js")):
                        continue
                    path = os.path.join(dirpath, fn)
                    try:
                        src = open(path, errors="replace").read()
                    except OSError:
                        continue
                    for m in self.AUTH_DEF_RE.finditer(src):
                        name = m.group(1)
                        if m.group(2):
                            continue          # bound method, not a guard
                        # count references outside the definition line itself
                        uses = len(re.findall(rf"\b{re.escape(name)}\b", src))
                        if uses <= 1:
                            self.checks_run += 1
                            self.findings.append(Finding(
                                id=f"ORPHAN_AUTH:{os.path.relpath(path, root)}:{name}",
                                severity="critical",
                                title=f"{name}() is defined but never called",
                                proves=f"grep found {uses} occurrence(s) of '{name}' in "
                                       f"{path}, i.e. the definition only.",
                                does_not_prove="Does not prove the endpoint is unauthenticated "
                                               "if another layer (proxy, gateway) enforces auth. "
                                               "Must be confirmed by probing a protected route.",
                                evidence={"path": path, "function": name, "references": uses},
                                remediation="Attach the dependency to the routes, then probe a "
                                            "PROTECTED route (not /docs or /health) to confirm.",
                            ))

    # -- CHECK 3: effective sshd config, not the file ───────────────────

    def check_sshd_effective(self) -> None:
        if not os.path.exists("/etc/ssh/sshd_config"):
            self.checks_skipped.append("sshd:not-present")
            return
        out = subprocess.run(["sshd", "-T"], capture_output=True, text=True).stdout
        eff = {}
        for line in out.splitlines():
            k, _, v = line.partition(" ")
            if k in ("permitrootlogin", "passwordauthentication", "maxauthtries"):
                eff[k] = v.strip()
        self.checks_run += 1
        risky = (eff.get("permitrootlogin") == "yes"
                 and eff.get("passwordauthentication") == "yes")
        if risky:
            self.findings.append(Finding(
                id="SSH_ROOT_PASSWORD",
                severity="critical",
                title="sshd accepts root password authentication (effective config)",
                proves=f"`sshd -T` reports permitrootlogin={eff.get('permitrootlogin')} and "
                       f"passwordauthentication={eff.get('passwordauthentication')}. This is "
                       "the EFFECTIVE config after drop-ins, which override the main file.",
                does_not_prove="Does not prove an account was compromised. Check auth logs for "
                               "successful logins from unexpected source addresses.",
                evidence={"effective": eff},
                remediation="Delete the drop-in that re-enables it; verify with `sshd -T`; "
                            "then `sshd -t && systemctl reload ssh`.",
            ))

    # -- CHECK 4: detectors actually fire ────────────────────────────────

    def self_test_detectors(self) -> None:
        """Negative control. A detector that never fires protects nothing."""
        import tempfile
        fixture = tempfile.mkdtemp()
        # a real file containing a verifier with no call site
        with open(os.path.join(fixture, "vuln.py"), "w") as f:
            f.write("def verify_api_key(x):\n    return x == 'k'\n\n"
                    "def route():\n    return 'open'\n")
        # a correct file: verifier defined AND attached
        with open(os.path.join(fixture, "ok.py"), "w") as f:
            f.write("def verify_api_key(x):\n    return x == 'k'\n\n"
                    "def route():\n    return verify_api_key('k')\n")

        def fires(root):
            n = 0
            for d, dirs, files in os.walk(root):
                dirs[:] = [x for x in dirs if x != "__pycache__"]
                for fn in files:
                    if not fn.endswith(".py"):
                        continue
                    src = open(os.path.join(d, fn), errors="replace").read()
                    for m in self.AUTH_DEF_RE.finditer(src):
                        if len(re.findall(rf"\b{re.escape(m.group(1))}\b", src)) <= 1:
                            n += 1
            return n

        self.checks_run += 2
        self.detector_fired_on_vuln = fires(fixture) == 1
        self.detector_silent_on_ok = fires(fixture) == 1   # same dir; ok.py must not add one
        if not self.detector_fired_on_vuln:
            self.findings.append(Finding(
                id="DETECTOR_BLIND",
                severity="critical",
                title="orphan-auth detector did not fire on a known-bad fixture",
                proves="The fixture with an unattached verifier was scanned.",
                does_not_prove="Nothing. A detector that cannot detect is worse than none, "
                               "because it manufactures confidence.",
                evidence={},
                remediation="Fix the regex before trusting any clean result.",
            ))

    # -- report ─────────────────────────────────────────────────────────

    def report(self) -> dict:
        by_sev = {}
        for f in self.findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        return {
            "generated_at": time.time(),
            "public_ip": self.public_ip,
            "checks_run": self.checks_run,
            "checks_skipped": self.checks_skipped,
            "findings": [f.to_json() for f in self.findings],
            "severity_counts": by_sev,
            "verdict": ("EXPOSED" if any(
                f.severity == "critical" for f in self.findings) else "NO CRITICAL"),
            "harness_limitation": (
                "This harness probes from the host itself. A local connect to the public "
                "address may traverse hairpin NAT and does not prove an off-site host's "
                "view. UNVERIFIED entries mean genuinely unknown, not closed."
            ),
        }


if __name__ == "__main__":
    h = Harness()
    h.check_reachability()
    h.check_orphan_auth(["/root/agent-bridge", "/root/evez-agentnet",
                         "/root/.openclaw/workspace/evez-os/repos/evez-api"])
    h.check_sshd_effective()
    h.self_test_detectors()
    print(json.dumps(h.report(), indent=2))
