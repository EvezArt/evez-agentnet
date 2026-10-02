"""Test MoE inference — including the thinking-budget bug that produced
silent empty answers.

Bug: qwen3 and deepseek-r1 emit a separate "thinking" field and spend
num_predict on chain-of-thought before answering. With num_predict=400 the
model thought until it hit the limit and returned response="" — a successful
HTTP 200 with no text. Without an explicit empty-response guard that reads as
success.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path("/root/evez-agentnet")
sys.path.insert(0, str(REPO))

spec = importlib.util.spec_from_file_location("moe_infer", REPO / "moe_infer.py")
MI = importlib.util.module_from_spec(spec)
sys.modules["moe_infer"] = MI
spec.loader.exec_module(MI)

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("payload construction — the regression guard")
captured = {}


def _fake_urlopen(req, timeout=None):
    captured["body"] = json.loads(req.data.decode())
    captured["url"] = req.full_url

    class R:
        def read(self):
            return json.dumps({
                "model": captured["body"]["model"],
                "response": "stub answer",
                "eval_count": 5,
                "done_reason": "stop",
            }).encode()

        def __enter__(self):
            return R()

        def __exit__(self, *a):
            return False

    return R()


# Snapshot the real roster BEFORE stubbing urlopen, otherwise the stub also
# intercepts moe_router.installed_experts() and routing has nothing to pick.
import moe_router as _MR
_real_experts = _MR.installed_experts()
import moe_router
moe_router.installed_experts = lambda *a, **k: _real_experts

import urllib.request
_real = urllib.request.urlopen
urllib.request.urlopen = _fake_urlopen
try:
    MI.generate("hello there", prefer="classify")
finally:
    urllib.request.urlopen = _real
    moe_router.installed_experts = _MR.installed_experts

body = captured["body"]
expect("think:false is sent", body.get("think") is False, str(body.get("think")))
expect("reasoning families get a larger budget",
       body["options"]["num_predict"] >= 1200,
       str(body["options"]["num_predict"]))
expect("model is the routed expert", body["model"] == "qwen3:0.6b", body["model"])
expect("stream is off", body.get("stream") is False)

print("\nempty response must be a FAILURE, not ok=True with ''")


def _empty_urlopen(req, timeout=None):
    class R:
        def read(self):
            return json.dumps({"model": "x", "response": "", "eval_count": 8,
                               "done_reason": "length",
                               "thinking": "lots of reasoning..."}).encode()

        def __enter__(self):
            return R()

        def __exit__(self, *a):
            return False

    return R()


urllib.request.urlopen = _empty_urlopen
try:
    r = MI.generate("hello", prefer="classify")
finally:
    urllib.request.urlopen = _real
expect("empty response reports ok=False", r["ok"] is False, str(r.get("ok")))
expect("error names the likely cause", "thinking" in r.get("error", ""),
       r.get("error", ""))
expect("thinking_chars is reported", r.get("thinking_chars", 0) > 0,
       str(r.get("thinking_chars")))

print("\nembed-only models can never be routed to generation")
from moe_router import installed_experts, route

experts = installed_experts()
moe_router.installed_experts = lambda *a, **k: _real_experts
urllib.request.urlopen = _fake_urlopen
try:
    re_ = MI.generate("embed this", prefer="embed")
finally:
    urllib.request.urlopen = _real
    moe_router.installed_experts = _MR.installed_experts
expect("embed kind does not produce an embed model",
       "nomic" not in (re_.get("expert") or ""), str(re_.get("expert")))

print("\nno route -> clear failure, not a default model")
# moe_infer does `from moe_router import route`, so the name is bound in
# moe_infer's namespace. Patching moe_router.route does nothing — that was
# the bug in this test.
_real_router = MI.route
MI.route = lambda *a, **k: type(
    "R", (), {"expert": None, "gate": "none", "task_kind": "",
              "reason": "ollama unreachable", "confidence": None})()
urllib.request.urlopen = _fake_urlopen
try:
    rn = MI.generate("anything")
finally:
    MI.route = _real_router
    urllib.request.urlopen = _real
expect("no expert -> ok=False", rn["ok"] is False, str(rn))
expect("reason surfaced", "ollama" in rn.get("error", ""), rn.get("error", ""))

print("\nlive inference (the real proof)")
urllib.request.urlopen = _real
if experts:
    live = MI.generate("Reply with exactly: ROUTER_OK", prefer="classify")
    expect("live generation succeeded", live["ok"] is True, str(live.get("error")))
    expect("live answer is non-empty", bool(live.get("text")), str(live)[:120])
    expect("provenance recorded", bool(live.get("expert")), str(live.get("expert")))
    print(f"       routed to {live.get('expert')} in {live.get('elapsed_s')}s")

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
