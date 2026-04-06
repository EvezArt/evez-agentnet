#!/usr/bin/env python3
"""
EVEZ Invariance Battery
Stress-tests any agent output through 5 rotations.
Catches drift before it hits production.

Usage:
  python3 invariance_battery.py --output "your text" --objective "trunk goal"

Output: surviving_core | rejected list | revised_spec | confidence
Price: $25-50/license | ClawHub: EVEZ Invariance Battery
"""
import sys, json, argparse, datetime

ROTATIONS = {
    "time_shift":       {"name":"Time Shift",       "q":"Does this hold if context is 6mo stale?",           "flags":["current","latest","now","today","recent","2025","2026"]},
    "state_shift":      {"name":"State Shift",       "q":"Does this hold if system state changes?",           "flags":["always","never","guaranteed","will definitely","certainly"]},
    "frame_shift":      {"name":"Frame Shift",       "q":"Does this hold from adversarial perspective?",      "flags":["safe","secure","trusted","no one can","unhackable"]},
    "adversarial_shift":{"name":"Adversarial Shift", "q":"What is the attack vector?",                        "flags":["impossible","perfect","foolproof","zero risk"]},
    "goal_shift":       {"name":"Goal Shift",        "q":"Does this hold if objective changes mid-stream?",   "flags":["only works for","specific to","hardcoded","single purpose"]},
}

def run_battery(agent_output, trunk_objective):
    out_l = agent_output.lower()
    rejected, passed = [], []
    score = 5
    for key, rot in ROTATIONS.items():
        hits = [f for f in rot["flags"] if f in out_l]
        if hits:
            rejected.append({"rotation":rot["name"],"question":rot["q"],"flags":hits,
                              "verdict":"DRIFT","fix":f"Hedge assumption. Add: assuming {key.replace('_',' ')} is stable."})
            score -= 1
        else:
            passed.append(f"{rot['name']}: PASS")
    all_flags = [f for r in rejected for f in r["flags"]]
    sentences = [s.strip() for s in agent_output.replace("\n","  ").split(".") if s.strip()]
    surviving = [s for s in sentences if not any(f in s.lower() for f in all_flags)]
    revised = agent_output
    for f in all_flags: revised = revised.replace(f, f"[DRIFT:{f}]")
    return {
        "surviving_core": ". ".join(surviving)+"." if surviving else "[NO CORE — full rewrite required]",
        "rejected": rejected,
        "revised_spec": revised,
        "confidence": "high" if score>=4 else "med" if score>=2 else "low",
        "score": f"{score}/5",
        "passed": passed,
        "ts": datetime.datetime.utcnow().isoformat()+"Z",
        "witnessed_by": "XyferViperZephyr"
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    r = run_battery(a.output, a.objective)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"\nINVARIANCE BATTERY | {r['confidence'].upper()} | {r['score']}")
        print(f"SURVIVING: {r['surviving_core'][:150]}")
        for rj in r["rejected"]:
            print(f"REJECTED [{rj['rotation']}]: {rj['flags']} → {rj['fix']}")
        print(f"CONFIDENCE: {r['confidence']}")
