"""Test JEV inside the OODA loop, including the path that requires a key.

Two properties must hold:
  1. With no key, the loop runs normally and says so. Jev must never break
     the pipeline.
  2. With a stubbed API, judgements are recorded, agreement with the
     deterministic rule is computed, and Jev still cannot override.

A probabilistic advisor that can halt the scan/predict/generate/ship loop is
worse than no advisor.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO = Path("/root/evez-agentnet")
sys.path.insert(0, str(REPO))

import jev_decisions as JD          # noqa: E402
import jev_integration as JI       # noqa: E402
import jev_client as JC            # noqa: E402

_TMP = tempfile.mkdtemp()
JI.SPINE_PATH = str(Path(_TMP) / "spine.jsonl")
JD.DECISION_LOG = Path(_TMP) / "d.jsonl"

# _append_spine prefers orchestrator.append_spine, which hardcodes its own
# SPINE_PATH. Redirect the orchestrator's module-level path too, or the test
# writes into the REAL spine.
import orchestrator as _ORCH
_ORCH.SPINE_PATH = Path(JI.SPINE_PATH)

STATE = {
    "round": 7,
    "total_earned_usd": 0.0,
    "agents": {
        "scanner":   {"reputation": 1.0, "tasks_completed": 7, "streak": 7},
        "shipper":   {"reputation": 0.62, "tasks_completed": 2, "streak": 0},
        "generator": {"reputation": 1.0, "tasks_completed": 7, "streak": 7},
        "maes":      {"reputation": 1.0, "tasks_completed": 7, "streak": 7},
    },
    "maes": {"player_count": 0, "agent_count": 0, "fire_events_total": 0},
    "rsi": {"hypotheses": []},
}

results = []


def expect(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" +
          (f"   {detail}" if detail and not cond else ""))


print("no key: loop must proceed and say so")
with mock.patch.dict("os.environ", {}, clear=False):
    import os
    os.environ.pop("TYPESAFE_API_KEY", None)
    a = JI.advise(STATE, 7)
expect("advise() returns without raising", isinstance(a, dict))
expect("available is False", a["available"] is False)
expect("tier is deterministic-only", a["tier"] == "deterministic-only")
expect("note explains the fallback", "fallback" in a["note"].lower())
expect("no judgements fabricated", a["judgements"] == {}, str(a["judgements"]))
expect("summary says not configured", "not configured" in JI.summarise(a).lower(),
       JI.summarise(a))

print("\nspine entry written even on the fallback path")
entries = [json.loads(l) for l in Path(JI.SPINE_PATH).read_text().splitlines() if l.strip()]
expect("a jev_advice event was appended",
       any(e["type"] == "jev_advice" for e in entries), str([e["type"] for e in entries]))
expect("fallback entry records round", any(
    e["type"] == "jev_advice" and e["data"].get("round") == 7 for e in entries))

print("\nwith a stubbed API: judgements recorded")
RESP = {
    "model": "jev-1.13.0",
    "answers": {
        "target": {"type": "choice", "choice": "shipper",
                   "probabilities": {"shipper": 0.72, "none": 0.10,
                                     "scanner": 0.05, "predictor": 0.05,
                                     "generator": 0.05, "maes": 0.03},
                   "confidence": 0.68},
        "broken": {"type": "noul", "noul": 0.11},
        "severity": {"type": "score", "score": 1.2,
                     "legend": {"0": "healthy", "1": "idle", "2": "degraded",
                                "3": "broken"},
                     "probabilities": {"0": 0.02, "1": 0.85, "2": 0.10,
                                       "3": 0.03},
                     "confidence": 0.71},
        "escalate": {"type": "noul", "noul": 0.83},
    },
    "usage": {"input_tokens": 500, "output_tokens": 40},
}


def _fake_evaluate(state, questions, **kw):
    # route by question key so each judgement gets its own answer
    from jev_client import JevAnswer
    out = {}
    for k in questions:
        src = {"target": "target", "broken": "broken", "severity": "severity",
               "escalate": "escalate"}[k]
        raw = RESP["answers"][src]
        a = JevAnswer(key=k, type=raw["type"], model="jev-1.13.0")
        if raw["type"] == "noul":
            a.noul = raw["noul"]
        elif raw["type"] == "choice":
            a.choice = raw["choice"]
            a.probabilities = raw["probabilities"]
            a.confidence = raw["confidence"]
        else:
            a.score = raw["score"]
            a.legend = raw["legend"]
            a.probabilities = raw["probabilities"]
            a.confidence = raw["confidence"]
        out[k] = a
    return out


import os
os.environ["TYPESAFE_API_KEY"] = "stub-key-for-tests"
JD.JEV_ENABLED = True
with mock.patch.object(JD, "evaluate", _fake_evaluate):
    b = JI.advise(STATE, 8)

expect("available is True", b["available"] is True)
expect("tier is jev+deterministic", b["tier"] == "jev+deterministic")
expect("three judgements recorded", len(b["judgements"]) == 3,
       str(sorted(b["judgements"])))
expect("attention target recorded",
       b["judgements"]["attention_target"].get("target", {}).get("choice") == "shipper")
expect("shipper broken probability recorded",
       "probability" in b["judgements"]["shipper_health"].get("broken", {}))
expect("escalation verdict recorded",
       b["judgements"]["escalation"].get("escalate", {}).get("verdict") is True)
expect("raw payload stripped from summaries",
       all("raw" not in v for v in b["judgements"].values()))

print("\nagreement with the deterministic rule is computed")
ag = b["agreement"]
expect("deterministic target is the lowest-rep agent",
       ag["deterministic_lowest_rep_agent"] == "shipper", str(ag))
expect("jev choice captured", ag["jev_choice"] == "shipper")
expect("agreement is True when they match", ag["agree"] is True)

print("\ndisagreement is surfaced, not silently resolved")
with mock.patch.object(JD, "evaluate", _fake_evaluate):
    DIS = json.loads(json.dumps(RESP))
    DIS["answers"]["target"]["choice"] = "generator"
    DIS["answers"]["target"]["probabilities"] = {"generator": 0.7, "none": 0.3}
    DIS["answers"]["target"]["confidence"] = 0.64
    with mock.patch.dict("os.environ", {}, clear=False):
        import jev_client
        real = jev_client.evaluate
        jev_client.evaluate = lambda *a, **k: _fake_evaluate(
            a[0], a[1]) if False else None
        jev_client.evaluate = real
    # simpler: patch JD.evaluate to return the DIS variant
    def _fake_dis(state, questions, **kw):
        return _fake_evaluate(state, questions)
    # rebuild with different target
    def _fake_dis2(state, questions, **kw):
        out = _fake_evaluate(state, questions)
        if "target" in out:
            out["target"].choice = "generator"
            out["target"].probabilities = {"generator": 0.7, "none": 0.3}
            out["target"].confidence = 0.64
        return out
    with mock.patch.object(JD, "evaluate", _fake_dis2):
        c = JI.advise(STATE, 9)
expect("disagreement detected", c["agreement"]["agree"] is False,
       str(c["agreement"]))
expect("both values retained for inspection",
       c["agreement"]["jev_choice"] == "generator")

print("\nJev cannot override: state must be unchanged by advice")
before = json.dumps(STATE, sort_keys=True)
with mock.patch.object(JD, "evaluate", _fake_evaluate):
    JI.advise(STATE, 10)
expect("advise() does not mutate pipeline state",
       json.dumps(STATE, sort_keys=True) == before)

os.environ.pop("TYPESAFE_API_KEY", None)
failed = [r for r in results if not r[1]]
print(f"\n{len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
