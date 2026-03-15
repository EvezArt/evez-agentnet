#!/usr/bin/env python3
"""
evez-agentnet Build Agent — 6-hour expansion cycle.
Reads network topology health, identifies weakest nodes,
opens GitHub Issues as build proposals (human gates all execution).
"""
import os, json, datetime, requests

GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "EvezArt"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

REPOS_MATURITY = {
    "evez-os": 0.6,
    "evez-agentnet": 0.7,
    "evez-autonomous-ledger": 0.8,
    "agentvault": 0.5,
    "evez-meme-bus": 0.65,
    "Evez666": 0.75,
}

# WIN condition from evez-os-v2
WIN_THRESHOLD = 0.831


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def get_repo_issues(repo):
    url = f"https://api.github.com/repos/{OWNER}/{repo}/issues?state=open&per_page=10"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else []


def score_repo(repo, maturity):
    issues = get_repo_issues(repo)
    issue_penalty = len([i for i in issues if "pull_request" not in i]) * 0.02
    return max(0.0, maturity - issue_penalty)


def call_claude(prompt):
    if not ANTHROPIC_KEY:
        return None
    import urllib.request
    body = json.dumps({
        "model": "claude-3-haiku-20240307",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["content"][0]["text"]


def open_build_issue(repo, title, body):
    url = f"https://api.github.com/repos/{OWNER}/{repo}/issues"
    r = requests.post(url, headers=HEADERS, json={
        "title": title,
        "body": body,
        "labels": ["autonomous-build", "needs-review"],
    })
    return r.status_code in (200, 201)


def main():
    print(f"\n🔨 evez-agentnet Build Agent — {now_iso()}")

    scores = {}
    for repo, maturity in REPOS_MATURITY.items():
        score = score_repo(repo, maturity)
        scores[repo] = score
        delta = WIN_THRESHOLD - score
        print(f"  {repo}: score={score:.3f} gap={delta:.3f}")

    # Target the 2 weakest repos for build proposals
    sorted_repos = sorted(scores.items(), key=lambda x: x[1])
    targets = sorted_repos[:2]

    for repo, score in targets:
        gap = WIN_THRESHOLD - score
        prompt = f"""You are the EVEZ build agent. Repo '{repo}' has maturity score {score:.3f},
gap to WIN threshold {gap:.3f}. Suggest ONE specific, actionable GitHub issue title and
3-sentence body that would most improve this repo's reliability and autonomy.
Format: TITLE: <title>\nBODY: <body>"""
        suggestion = call_claude(prompt)
        if suggestion and "TITLE:" in suggestion:
            lines = suggestion.strip().split("\n")
            title = next((l.replace("TITLE:", "").strip() for l in lines if l.startswith("TITLE:")), None)
            body_lines = [l.replace("BODY:", "").strip() for l in lines if l.startswith("BODY:")]
            body = body_lines[0] if body_lines else suggestion
            if title:
                full_body = f"{body}\n\n*🤖 Auto-proposed by build_agent.py | Score: {score:.3f} | WIN gap: {gap:.3f} | Requires human approval before any action.*"
                opened = open_build_issue(repo, f"🔨 [BUILD] {title}", full_body)
                print(f"  {'\u2705' if opened else '\u274c'} Build issue opened on {repo}: {title[:50]}")
        else:
            print(f"  ⚠️  No Claude suggestion for {repo} (key missing or parse fail)")

    print("  ✅ Build agent complete.")


if __name__ == "__main__":
    main()
