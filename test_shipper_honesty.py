"""Prove the shipper no longer claims false success.

The defect being tested: 747 "shipped" records, $0.00. Every delivery path
was a TODO stub while the log said "Shipped". These tests assert a draft is
marked shipped ONLY when a real transmission succeeds.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ship_under_test", "/root/evez-agentnet/shipper/ship_agent.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("no channel configured -> must NOT claim shipped")
S.TWITTER_BEARER = ""
S.MASTODON_TOKEN = ""
S.GUMROAD_TOKEN = ""
S.SHIP_LOG = Path(tempfile.mkdtemp()) / "ship.jsonl"

drafts = [
    {"type": "twitter_thread", "title": "t", "content": "hello world this is long"},
    {"type": "gumroad_report", "title": "g", "content": "x"},
    {"type": "github_post", "title": "gh", "content": "y"},
    {"type": "mystery_type", "title": "m"},
]
s = S.run(drafts)
expect("attempted counts every draft", s["attempted"] == 4, str(s))
expect("zero shipped when nothing is configured", s["shipped"] == 0, str(s))
expect("earned is zero", s["earned_usd"] == 0.0, str(s))
expect("twitter reports channel_not_configured",
       s["reasons"].get("channel_not_configured", 0) >= 1, str(s["reasons"]))
expect("github_post reports not_implemented",
       s["reasons"].get("delivery_not_implemented", 0) >= 2, str(s["reasons"]))

print("\nevery log record must carry a reason, not a bare 'shipped'")
rows = [json.loads(l) for l in S.SHIP_LOG.read_text().splitlines() if l.strip()]
expect("one log row per draft", len(rows) == 4, f"{len(rows)}")
expect("no row claims plain 'shipped'",
       all(r["status"] != "shipped" for r in rows),
       str([r["status"] for r in rows]))
expect("every row states why", all(r["status"].startswith("not_shipped")
                                  for r in rows), str([r["status"] for r in rows]))
expect("log records which channels were available",
       all("channels_available" in r for r in rows))

print("\nempty content must not be reported as a ship")
S.SHIP_LOG = Path(tempfile.mkdtemp()) / "ship.jsonl"
s2 = S.run([{"type": "twitter_thread", "title": "e", "content": "   "}])
expect("empty twitter content not shipped", s2["shipped"] == 0, str(s2))
expect("reason is empty_content",
       s2["reasons"].get("empty_content", 0) == 1, str(s2["reasons"]))

print("\na failing API must be a failure, not a success")


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def read(self):
        return json.dumps(self._p).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


S.SHIP_LOG = Path(tempfile.mkdtemp()) / "ship.jsonl"
S.TWITTER_BEARER = "fake-token-for-test"
import urllib.error


def _boom(req, timeout=20):
    raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)


_orig = urllib.request.urlopen if hasattr(urllib, "request") else None
import urllib.request
_real = urllib.request.urlopen
urllib.request.urlopen = _boom
try:
    s3 = S.run([{"type": "twitter_thread", "title": "r", "content": "a real tweet body"}])
finally:
    urllib.request.urlopen = _real
expect("HTTP 429 yields zero shipped", s3["shipped"] == 0, str(s3))
expect("HTTP error reason recorded", s3["reasons"].get("api_error", 0) == 1,
       str(s3["reasons"]))

print("\nregression guard — the original signature")
import inspect
sig = inspect.signature(S.run)
expect("run() takes drafts", list(sig.parameters) == ["drafts"], str(sig))

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
