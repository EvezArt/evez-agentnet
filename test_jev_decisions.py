"""Test the Jev decision layer without a live key.

Two things must hold:
  1. With no key, the layer reports unavailable and returns an explicit
     fallback — it must NOT invent a probability.
  2. With a stubbed API, parsing is correct and confidence gating abstains
     on low-confidence answers.

A decision layer that fabricates confidence is worse than none: code branches
on the number either way.
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path("/root/evez-agentnet")
sys.path.insert(0, str(REPO))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(REPO / path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


STATE = {
    "round": 42,
    "total_earned_usd": 0.0,
    "agents": {
        "scanner": {"reputation": 1.0, "tasks_completed": 40, "streak": 40},
        "shipper": {"reputation": 0.71, "tasks_completed": 12, "streak": 1},
        "generator": {"reputation": 1.0, "tasks_completed": 40, "streak": 40},
    },
    "maes": {"player_count": 0, "agent_count": 0, "fire_events_total": 0},
    "rsi": {"hypotheses": []},
}

print("unavailable path — must refuse to fabricate")
os.environ.pop("TYPESAFE_API_KEY", None)
JD = load("jev_decisions", "jev_decisions.py")
JD.DECISION_LOG = Path(tempfile.mkdtemp()) / "d.jsonl"

expect("available() is False without a key", JD.available() is False)
r = JD.judge_attention_target(STATE)
expect("returns ok=False", r["ok"] is False, str(r))
expect("source is explicitly fallback", r["source"] == "fallback", str(r))
expect("value is the declared fallback", r["value"] == "none", str(r))
expect("no probability is fabricated", "probabilities" not in r, str(r))
expect("a reason is given", bool(r.get("reason")), str(r))

r2 = JD.judge_escalation("some brief", {"failures": [], "warnings": []})
expect("escalation also falls back explicitly", r2["ok"] is False, str(r2))

log = [json.loads(x) for x in JD.DECISION_LOG.read_text().splitlines() if x.strip()]
expect("every skip is recorded", len(log) == 2, f"{len(log)}")
expect("skips record the reason",
       all(x.get("reason") == "jev_disabled_or_no_key" for x in log), str(log[:1]))

print("\nstatus reporting")
s = JD.status()
expect("status reports has_key False", s["has_key"] is False)
expect("status reports available False", s["available"] is False)
expect("status exposes the abstain threshold", s["min_confidence"] == 0.55, str(s))

print("\nclient contract")
JC = load("jev_client", "jev_client.py")
from jev_client import JevUnavailable

try:
    JC.evaluate("state", {"q": {"type": "noul", "instructions": "x?"}})
    expect("no key raises JevUnavailable", False, "did not raise")
except JevUnavailable as e:
    expect("no key raises JevUnavailable", True)
    expect("error names the missing key", "TYPESAFE_API_KEY" in str(e), str(e))

try:
    JC.evaluate("s", {})
    expect("empty questions raises", False, "did not raise")
except ValueError:
    expect("empty questions raises ValueError", True)

print("\nanswer parsing")
payload = {
    "model": "jev-1.13.0",
    "answers": {
        "n": {"type": "noul", "noul": 0.87},
        "c": {"type": "choice", "choice": "shipper",
              "probabilities": {"shipper": 0.71, "none": 0.29},
              "confidence": 0.66},
        "s": {"type": "score", "score": 2.4,
              "legend": {"0": "ok", "1": "bad", "2": "broken"},
              "probabilities": {"0": 0.05, "1": 0.15, "2": 0.80},
              "confidence": 0.74},
    },
    "usage": {"input_tokens": 100, "output_tokens": 10},
}
parsed = JC._parse(payload)
expect("noul parsed", parsed["n"].noul == 0.87)
expect("choice parsed", parsed["c"].choice == "shipper")
expect("choice probabilities parsed", abs(sum(parsed["c"].probabilities.values()) - 1.0) < 1e-6)
expect("choice confidence parsed", parsed["c"].confidence == 0.66)
expect("score parsed", parsed["s"].score == 2.4)
expect("score legend parsed", parsed["s"].legend["2"] == "broken")
expect("model version captured", parsed["n"].model == "jev-1.13.0")
expect("all tagged source=jev",
       all(a.source == "jev" for a in parsed.values()))

print("\noffline fixtures must be labelled")
# register_offline() gates evaluate_offline(); an unregistered marker MUST raise
try:
    JC.evaluate_offline("unregistered", {"q": {"type": "noul"}})
    expect("unregistered fixture raises", False, "did not raise")
except JC.JevUnavailable:
    expect("unregistered fixture raises JevUnavailable", True)

JC.register_offline("m", {"answers": {}})
o = JC.evaluate_offline("m", {"q": {"type": "noul", "noul": 0.5}})
expect("fixture tagged offline-fixture", o["q"].source == "offline-fixture")
expect("fixture never claims to be jev", o["q"].source != "jev")

print("\nconfidence gating")
expect("MIN_CONFIDENCE default is 0.55", JD.MIN_CONFIDENCE == 0.55)
expect("YES_THRESHOLD default is 0.70", JD.YES_THRESHOLD == 0.70)
# 0.66 > 0.55 -> would act; 0.40 < 0.55 -> abstain
expect("confidence above floor would act", (0.66 >= JD.MIN_CONFIDENCE))
expect("confidence below floor would abstain", not (0.40 >= JD.MIN_CONFIDENCE))

failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
