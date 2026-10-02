"""Defensive self-audit: what does an adversary get from the public repos?

Uses only public sources (GitHub API + shallow clones of public repos).
Reports EXPOSURE, never copies secrets. Any credential-shaped string is
redacted to a fingerprint so it can be rotated without reprinting it.
"""
import json
import re
import subprocess
import urllib.request
from pathlib import Path

UA = {"User-Agent": "EVEZ-selfaudit", "Accept": "application/vnd.github+json"}
OUT = Path("/tmp/evez_audit")
OUT.mkdir(exist_ok=True)

# credential-shaped patterns; capture a fingerprint, never the value
PATTERNS = {
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_pat": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "stripe_live": re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b"),
    "google_api": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "bearer_literal": re.compile(r"[Bb]earer\s+[A-Za-z0-9._-]{28,}"),
    "tailscale_key": re.compile(r"\btskey-[a-z]+-[A-Za-z0-9]{20,}\b"),
    "generic_secret_assign": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|passwd|password|token)\s*[=:]\s*[\"'][^\"'\s]{16,}[\"']"),
}

# filenames that should never be committed
SUSPECT_NAMES = re.compile(
    r"(^\.env($|\.)|id_rsa|id_ed25519|\.pem$|\.key$|credentials\.json|"
    r"secrets?\.(ya?ml|json)$|\.netrc|\.pgpass|shadow$|^\.aws/)", re.I)


def fp(kind: str, val: str) -> str:
    import hashlib
    h = hashlib.sha256(val.encode()).hexdigest()[:12]
    return f"{kind}:{h}"


def api(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def main():
    repos = api("https://api.github.com/users/EvezArt/repos?per_page=100")
    own = [r for r in repos if not r["fork"]]
    print(f"scanning {len(own)} public repos for credential-shaped strings\n")

    findings = {}
    scanned = 0
    for r in own:
        name = r["name"]
        url = r["clone_url"]
        dest = OUT / name
        if dest.exists():
            subprocess.run(["rm", "-rf", str(dest)], check=False)
        p = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            capture_output=True, text=True, timeout=180)
        if p.returncode != 0:
            continue
        scanned += 1

        for f in dest.rglob("*"):
            if not f.is_file() or ".git" in f.parts:
                continue
            rel = f.relative_to(dest)

            if SUSPECT_NAMES.search(f.name) or SUSPECT_NAMES.search(str(rel)):
                findings.setdefault(name, {"suspect_filenames": set()})
                findings[name]["suspect_filenames"].add(str(rel))

            if f.stat().st_size > 3_000_000:
                continue
            try:
                text = f.read_text(errors="ignore")
            except Exception:
                continue
            for kind, rx in PATTERNS.items():
                for m in rx.finditer(text):
                    key = f"{kind}"
                    findings.setdefault(name, {"secrets": set(), "suspect_filenames": set()})
                    findings[name].setdefault("secrets", set()).add(
                        fp(kind, m.group(0)[:64]))
                    findings[name].setdefault("where", set()).add(
                        f"{rel}:{text[:m.start()].count(chr(10))+1}")

    print(f"cloned & scanned: {scanned}/{len(own)}\n")

    if not findings:
        print("NO credential-shaped strings found in current HEAD of any public repo.")
        return 0

    for name, d in sorted(findings.items()):
        secs = d.get("secrets", set())
        files = d.get("suspect_filenames", set())
        print(f"[{name}]")
        if secs:
            print(f"  {len(secs)} credential-shaped string(s): {', '.join(sorted(secs))}")
            for w in sorted(d.get("where", set()))[:4]:
                print(f"      at {w}")
        if files:
            print(f"  suspect filenames: {', '.join(sorted(files)[:6])}")
        print()

    print("NOTE: this scans HEAD only. History can retain deleted secrets —")
    print("      check full history separately if any of the above is real.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
