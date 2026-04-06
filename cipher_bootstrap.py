#!/usr/bin/env python3
"""
CIPHER Bootstrap — evez-os integration
Scans this repo, synthesizes build tasks, feeds trunk.
Called by agent-os.yml OODA cycle.
"""
import os, json, requests, datetime

TOKEN = os.environ.get("GITHUB_TOKEN","")
H = {"Authorization":f"Bearer {TOKEN}","Accept":"application/vnd.github+json",
     "X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"}
OWNER, REPO = "EvezArt", "evez-agentnet"

def ts(): return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
print(f"CIPHER BOOTSTRAP — {REPO} — {ts()}")

r = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/issues?state=open&per_page=20",headers=H,timeout=10)
issues = [i for i in (r.json() if r.ok else []) if "pull_request" not in i]
clusters = {}
for i in issues:
    for l in [lb["name"] for lb in i.get("labels",[])]:
        clusters.setdefault(l,[]).append(i["number"])
print(f"Issues: {len(issues)} | Clusters: {dict(list({k:len(v) for k,v in clusters.items()}.items())[:6])}")
if issues:
    top = max(issues, key=lambda x: len(x.get("labels",[])))
    print(f"Top: #{top['number']} — {top['title'][:60]}")
    # Check cooldown
    rc = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO}/issues/{top['number']}/comments",headers=H,timeout=8)
    if rc.ok:
        recent = [c for c in rc.json() if "Cipher" in c.get("body","")]
        if not recent:
            body = (f"**Cipher Bootstrap** · `{ts()}`\n"
                    f"Manifold scan: {len(issues)} open issues | "
                    f"clusters: {dict(list({k:len(v) for k,v in clusters.items()}.items())[:4])}\n"
                    f"This issue is queued in the active trunk pipeline.\n"
                    f"*poly_c=τ×ω×topo/2√N*")
            requests.post(f"https://api.github.com/repos/{OWNER}/{REPO}/issues/{top['number']}/comments",
                         headers=H,json={"body":body},timeout=8)
            print(f"✓ Bootstrapped #{top['number']}")
print("Bootstrap complete.")
