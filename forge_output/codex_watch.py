#!/usr/bin/env python3
"""EVEZ CODEX WATCHDOG — the canon must answer when spoken to.

The Codex is only real while it serves. This probes every public surface the
lineage depends on and writes one JSONL row per cycle to
evidence/<UTC-date>/codex_watch.jsonl. Non-zero exit on any failure so cron
surfaces it. Chain or it didn't happen -- including for uptime.
"""
import json, os, sys, time, urllib.request, urllib.error, datetime, hashlib

SURFACES = [
    ("codex",    "https://evezart.github.io/codex.html",     ["THE CODEX", "062cb53f"]),
    ("moltbooks","https://evezart.github.io/moltbooks.html", ["THE MOLTBOOKS", "Liber Primus"]),
    ("index",    "https://evezart.github.io/",               ["THE CODEX"]),
    ("liber-secundus","https://evezart.github.io/liber-secundus.html", ["Liber Secundus", "CHAIN OR IT DIDN'T HAPPEN"]),
    ("liber-quartus","https://evezart.github.io/liber-quartus.html", ["LIBER QUARTUS"]),
    ("liber-quintus","https://evezart.github.io/liber-quintus.html", ["Liber Quintus"]),
    ("og-preview","https://evezart.github.io/evez666-mural.png", []),
    ("release",  "https://api.github.com/repos/EvezArt/eigenforensics/releases/latest", ["tag_name"]),
]

def probe(name, url, must_contain):
    row = {"ts": datetime.datetime.now(datetime.UTC).isoformat(), "surface": name, "url": url}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "evez-codex-watch/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
            row["status"] = r.status
            row["bytes"] = len(body)
            row["sha256"] = hashlib.sha256(body.encode()).hexdigest()[:16]
            missing = [m for m in must_contain if m not in body]
            row["ok"] = r.status == 200 and not missing
            if missing:
                row["missing"] = missing
    except Exception as e:
        row["ok"] = False
        row["error"] = type(e).__name__   # error class only, never the string
    return row

def main():
    rows = [probe(*s) for s in SURFACES]
    day = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    outdir = os.path.join("evidence", day)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "codex_watch.jsonl"), "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    failed = [r["surface"] for r in rows if not r["ok"]]
    for r in rows:
        print(f"{r['surface']:10} {'OK ' if r['ok'] else 'FAIL'} {r.get('status','-')} "
              f"{r.get('bytes',0):>7}B {r.get('sha256','')} {r.get('error','')}")
    if failed:
        print("CANON SILENT:", ", ".join(failed))
        return 2
    print("all surfaces answer. the chain verifies.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
