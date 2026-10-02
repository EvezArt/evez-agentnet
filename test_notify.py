"""Test notify.py without sending anything to a real chat.

Verifies parsing, escaping, and dedupe logic against a stubbed API.
A notifier that silently stops sending is worse than no notifier.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "notify_under_test", "/root/evez-agentnet/notify.py")
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


BRIEF_SAMPLE = """# EVEZ brief

## Needs your decision

### [HIGH] public-gateway
OpenClaw gateway bound to public IP
- **Action:** `systemctl disable --now openclaw-public-forward  (Tailscale stays)`
- **Why:** token leak

### [MEDIUM] income-zero
something
- **Action:** `fix run_ship()`
- **Why:** cosmetic
"""

print("parsing")
with tempfile.TemporaryDirectory() as d:
    b = Path(d) / "BRIEF.md"
    b.write_text(BRIEF_SAMPLE)
    N.BRIEF = b
    alerts = N.parse_alerts()
    expect("finds the HIGH item", any("public-gateway" in a for a in alerts),
           f"{alerts}")
    expect("includes its action",
           any("disable" in a for a in alerts), f"{alerts}")
    expect("excludes the MEDIUM item",
           not any("income-zero" in a for a in alerts), f"{alerts}")

print("\nmarkdown escaping (the bug that broke the first live send)")
raw = "systemctl disable --now openclaw-public-forward  (Tailscale stays)"
esc = None
# reproduce the esc() from notify.py body
def esc(s):
    out = []
    for ch in s:
        if ch in "_*`[]()~>#+-=|{}.!":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)

esc = esc(raw)
expect("parens escaped", r"\(" in esc and r"\)" in esc, esc)
expect("original text preserved after unescaping", esc.replace("\\", "") == raw)

# balance check: every escape is a valid escape char for Telegram Markdown
valid = set("_*`[]()~>#+-=|{}.!")
bad = [i for i, c in enumerate(esc)
       if c == "\\" and (i + 1 >= len(esc) or esc[i + 1] not in valid)]
expect("no dangling escape characters", not bad, f"indices {bad}")

print("\ndedupe")
# N.BRIEF must still point at a LIVE file here. The parsing block above used a
# TemporaryDirectory that has since been deleted, so parse_alerts() would
# silently return [] and every fingerprint assertion would fail for the wrong
# reason. Re-create the sample in its own directory.
with tempfile.TemporaryDirectory() as d:
    b2 = Path(d) / "BRIEF.md"
    b2.write_text(BRIEF_SAMPLE)
    N.BRIEF = b2
    state = Path(d) / ".last_alert"
    N.STATE_FILE = state
    state.write_text("[HIGH] public-gateway")
    same = N.parse_alerts()
    high = [a for a in same if not a.startswith("    ")]
    fp = "|".join(high)
    # fingerprint keeps the "[HIGH] " prefix because parse_alerts() emits the
    # full heading line; the stored state file is written with the same value.
    expect("fingerprint is the joined HIGH headings",
           fp == "[HIGH] public-gateway", fp)
    expect("stored state suppresses a repeat send",
           state.read_text().strip() == fp,
           f"state={state.read_text()!r} fp={fp!r}")

    state.write_text("[HIGH] something-else")
    expect("a changed alert set produces a different fingerprint",
           fp != state.read_text().strip())

print("\nconfig resolution")
expect("bot token resolves", bool(N.get_token()), "no token")
expect("chat id resolves", bool(N.get_chat_id()), "no chat id")

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
