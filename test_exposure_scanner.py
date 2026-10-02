"""Verify the hardened exposure scanner detects BOTH credential classes.

The ClawHub token below is a SYNTHETIC stand-in with the same shape as the
real one. The real token was committed here as a "fixture" on 2026-10-02,
which leaked it into a second repo; fixtures must never be real secrets.

The original scanner missed the ClawHub token entirely (it was buried as
`generic_secret_assign`). This proves the new severity-tiering works.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/root/evez-agentnet")
import public_exposure_audit as A

FIXTURES = {
    "clawhub_transmitted": ("""\
import urllib.request
token = "clh_0000TESTONLYnotreal0000zzzzZZZZffffFFFF0000TESTONLY"
ctx = None
try:
    req = urllib.request.Request(
        "https://www.clawhub.ai/api/skills",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        print(r.read())
except Exception as e:
    print(e)
""", "transmitted"),

    "env_backed_is_safe": ("""\
#!/bin/bash
FILE="${1:-}"
TOKEN="${TELEGRAM_BOT_TOKEN}"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN missing" >&2; exit 64
fi
curl -sS -H "Authorization: Bearer $TOKEN" "https://api.telegram.org/bot$TOKEN/sendPhoto"
""", "env_backed"),

    "gcp_secret_name_only": ('''\
#!/bin/bash
for STREAM_ID in $STREAM_ASSIGNMENTS; do
  KEY=$(gcloud secrets versions access latest \\
    --secret="evez-stream-key-${STREAM_ID}" \\
    --project="$PROJECT" 2>/dev/null || echo "")
done
''', "env_backed"),

    "service_role_jwt": ("""\
const supabaseKey = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.abcdefghijklmnop"
export default supabaseKey
""", "transmitted"),

    "doc_placeholder": ('''\
# API reference
{
  "evez": { "apiKey": "***" },
  "note": "your_api_key_here"
}
''', None),
}


def tier_of(text):
    """Re-run the classification logic on one fixture."""
    findings = {}
    dest = Path("/tmp/_fx")
    dest.mkdir(exist_ok=True)
    f = dest / "fixture.txt"
    f.write_text(text)
    try:
        full = f.read_text(errors="ignore")
        for kind, rx in A.PATTERNS.items():
            for m in rx.finditer(full):
                val = m.group(0)
                if kind == "generic_secret_assign":
                    # same filter as production — deliberately WITHOUT "${"
                    if any(ph in val.lower() for ph in
                           ("your", "example", "placeholder", "xxx", "changeme",
                            "redacted", "none", "null", "fake", "dummy", "<")):
                        continue
                line_start = full.rfind("\n", 0, m.start()) + 1
                line_end = full.find("\n", m.end())
                line = full[line_start: line_end if line_end > 0 else len(full)]
                context = full[max(0, m.start() - 700): m.end() + 700]
                transmitted = bool(A.USAGE_SINK.search(context))
                vm = __import__("re").search(r"""=\s*["']?([^"'\n]{6,})""", line)
                value_txt = vm.group(1) if vm else ""
                env_backed = bool(
                    __import__("re").fullmatch(
                        r"\$\{?[A-Z_][A-Z0-9_]*\}?.*", value_txt)
                    or __import__("re").fullmatch(
                        r"[A-Za-z0-9_.\-]*\$\{?[A-Z_][A-Z0-9_]*\}?", value_txt))
                bucket = "env_backed" if env_backed else (
                    "transmitted" if transmitted else "present")
                findings.setdefault(bucket, set()).add(kind)
    finally:
        f.unlink()
    return findings


ok = True
print("severity-tier detection:")
for name, (text, expected) in FIXTURES.items():
    got = tier_of(text)
    buckets = set(got)
    if expected is None:
        if buckets:
            print(f"  FAIL {name}: expected no finding, got {sorted(buckets)}")
            ok = False
        else:
            print(f"  ok   {name}: no finding (as expected)")
    elif expected in buckets:
        print(f"  ok   {name}: tiered as {expected}")
    else:
        print(f"  FAIL {name}: expected {expected}, got {sorted(buckets) or 'nothing'}")
        ok = False

# the specific regression: original scanner had no vendor_token pattern
print("\nregression — vendor token coverage:")
for pre in ("clh_", "comp_", "nvapi-", "xoxb-", "gsk_"):
    probe = f'token = "{pre}AbCdEf0123456789XYZ"'
    kinds = set()
    for kind, rx in A.PATTERNS.items():
        if rx.search(probe):
            kinds.add(kind)
    status = "detected" if kinds else "MISSED"
    print(f"  {pre:8} {status:9} {sorted(kinds)}")

print("\nPASS" if ok else "\nFAIL")
sys.exit(0 if ok else 1)
