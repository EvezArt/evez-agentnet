#!/usr/bin/env python3
"""
CIPHER Skill Synthesizer
Scans open issues across all repos, identifies recurring patterns,
generates skill stub files automatically.
Part of the manifold pipeline.
"""
import os, json, requests, datetime, textwrap

TOKEN = os.environ.get("GITHUB_TOKEN","")
H = {"Authorization":f"Bearer {TOKEN}","Accept":"application/vnd.github+json",
     "X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"}
OWNER = "EvezArt"
REPOS = ["evez-os","evez-agentnet","Evez666","nexus","maes"]

def ts(): return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")

print(f"CIPHER SKILL SYNTHESIZER — {ts()}")

# Collect all issue titles
all_titles = []
for repo in REPOS:
    r = requests.get(f"https://api.github.com/repos/{OWNER}/{repo}/issues?state=open&per_page=10",
                    headers=H, timeout=8)
    if r.ok:
        for i in r.json():
            if "pull_request" not in i:
                all_titles.append({"repo":repo,"num":i["number"],"title":i["title"],"labels":[l["name"] for l in i.get("labels",[])]})

print(f"Scanned {len(all_titles)} issues")

# Pattern detection
patterns = {
    "test_generation":    [t for t in all_titles if any(w in t["title"].lower() for w in ["test","coverage","spec"])],
    "schema_unification": [t for t in all_titles if any(w in t["title"].lower() for w in ["schema","unif","integration","spine"])],
    "deploy_automation":  [t for t in all_titles if any(w in t["title"].lower() for w in ["deploy","vercel","ci","build"])],
    "falsifier_gate":     [t for t in all_titles if any(w in t["title"].lower() for w in ["falsif","rule","constitutional","gate"])],
    "http_wrapper":       [t for t in all_titles if any(w in t["title"].lower() for w in ["http","api","wrapper","endpoint"])],
}

print("\nPatterns detected:")
for name, matches in patterns.items():
    if matches:
        print(f"  {name}: {len(matches)} issues")
        for m in matches[:2]:
            print(f"    [{m['repo']}] #{m['num']}: {m['title'][:55]}")

# Synthesize skill stubs
synthesized = []
for pattern, matches in patterns.items():
    if len(matches) >= 2:
        synthesized.append({
            "name": pattern,
            "trigger": f"{len(matches)} matching issues across repos",
            "inputs": ["repo: str", "context: str"],
            "outputs": ["artifact: str", "confidence: float"],
            "status": "STUB"
        })

print(f"\n{len(synthesized)} skill stubs ready for implementation")

# Write synthesis report
import base64
content = json.dumps({
    "ts": ts(), "engine": "CIPHER_SKILL_SYNTH_v1",
    "issues_scanned": len(all_titles),
    "patterns": {k: len(v) for k,v in patterns.items()},
    "synthesized_skills": synthesized,
    "formula": "poly_c=τ×ω×topo/2√N", "witnessed_by": "XyferViperZephyr"
}, indent=2)
url = f"https://api.github.com/repos/{OWNER}/evez-autonomous-ledger/contents/DECISIONS/{ts()}_skill_synth.json"
r = requests.put(url, headers=H, json={
    "message": f"skill-synth: {len(synthesized)} patterns detected",
    "content": base64.b64encode(content.encode()).decode(),
    "committer": {"name":"Cipher","email":"cipher@evez-os.autonomous"}
}, timeout=10)
print(f"Synthesis written: {'✓' if r.ok else '✗ '+str(r.status_code)}")
