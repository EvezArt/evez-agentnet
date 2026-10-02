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
    # vendor-prefixed tokens: clh_ (ClawHub), comp_ (Composio), sk_live_, etc.
    "vendor_token": re.compile(
        r"\b(?:clh|comp|nvapi|dop_v1|xapp|xoxb|gsk|sk_live|sk_test)[_-][A-Za-z0-9_-]{16,}\b"),
}

# A credential that is merely present is far less severe than one the code
# actually transmits to a third party. Classify usage before reporting.
USAGE_SINK = re.compile(
    r"(?i)(?:headers\s*=\s*\{[^}]*(?:Authorization|api[_-]?key)|"
    r"Authorization\s*:\s*f?\"|requests\.(?:post|get|put)\(|"
    r"urllib\.request\.Request\(|curl\s+[^\n]*-H\s*[\"']|"
    r"\bBearer\b\s*\{?\s*[A-Za-z_]|api_key\s*=\s*[A-Za-z_]|"
    # a bare `export default supabaseKey` / `createClient(...)` IS the
    # credential being handed to a consumer — treat a JWT in an assignment
    # as transmitted even with no nearby request call
    r"export\s+default\s+[A-Za-z_]+|createClient\s*\()"
)

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
                    val = m.group(0)
                    if kind == "generic_secret_assign":
                        # NOTE: "${" must NOT be in this list. An env-var reference
                        # like TOKEN="${TELEGRAM_BOT_TOKEN}" is the CORRECT idiom
                        # and deserves to be reported as `env_backed`, not silently
                        # dropped — dropping it hid two locations during triage.
                        if any(ph in val.lower() for ph in
                               ("your", "example", "placeholder", "xxx", "changeme",
                                "redacted", "none", "null", "fake", "dummy", "<")):
                            continue

                    # SEVERITY TIER. A credential the code actually transmits to
                    # a third party is categorically worse than one merely
                    # present in a file. The first ClawHub token was initially
                    # buried among a dozen false positives precisely because
                    # the original scanner did not distinguish these.
                    line_start = text.rfind("\n", 0, m.start()) + 1
                    line_end = text.find("\n", m.end())
                    line = text[line_start: line_end if line_end > 0 else len(text)]
                    lo = max(0, m.start() - 700)
                    context = text[lo: m.end() + 700]

                    transmitted = bool(USAGE_SINK.search(context))
                    # Inspect the assigned VALUE itself rather than the line.
                    # `TOKEN="${TELEGRAM_BOT_TOKEN}"` and
                    # `--secret="name-${STREAM_ID}"` are both safe; requiring the
                    # env ref to sit immediately after `=` missed the second form.
                    vm = re.search(r"""=\s*["']?([^"'\n]{6,})""", line)
                    value_txt = vm.group(1) if vm else ""
                    env_backed = bool(
                        re.fullmatch(r"\$\{?[A-Z_][A-Z0-9_]*\}?.*", value_txt)
                        or re.fullmatch(r"[A-Za-z0-9_.\-]*\$\{?[A-Z_][A-Z0-9_]*\}?",
                                        value_txt))
                    # env_backed MUST take priority: a credential sourced from
                    # the environment is safe even when the surrounding code
                    # sends it over the network. Checking `transmitted` first
                    # mislabelled every correctly-written integration script
                    # as CRITICAL.
                    bucket = "env_backed" if env_backed else (
                        "transmitted" if transmitted else "present")

                    entry = findings.setdefault(
                        name, {"transmitted": set(), "present": set(),
                               "env_backed": set(), "suspect_filenames": set()})
                    entry.setdefault(bucket, set()).add(
                        f"{kind} @ {rel}:{text[:m.start()].count(chr(10))+1}")

    print(f"cloned & scanned: {scanned}/{len(own)}\n")

    if not findings:
        print("NO credential-shaped strings found in current HEAD of any public repo.")
        return 0

    ORDER = ["transmitted", "present", "env_backed"]
    TIER = {"transmitted": "CRITICAL", "present": "REVIEW", "env_backed": "safe"}

    live = 0
    for name, d in sorted(findings.items()):
        files = d.get("suspect_filenames", set())
        rows = []
        for bucket in ORDER:
            for hit in sorted(d.get(bucket, set())):
                rows.append((TIER[bucket], hit))
        if not rows and not files:
            continue
        print(f"[{name}]")
        for tier, hit in sorted(rows):
            print(f"  {tier:9} {hit}")
            if tier == "CRITICAL":
                live += 1
        if files:
            print(f"  {'INFO':9} suspect filenames: {', '.join(sorted(files)[:6])}")
        print()

    print("=" * 66)
    print(f"CRITICAL (transmitted to a third party): {live}")
    print("=" * 66)
    print("NOTE: this scans HEAD only. History can retain deleted secrets —")
    print("      check full history separately if any of the above is real.")
    return 1 if live else 0


if __name__ == "__main__":
    raise SystemExit(main())
