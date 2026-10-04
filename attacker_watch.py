#!/usr/bin/env python3
"""attacker_watch.py — standing watch for the May 21/22 2026 DMZHOST attack ecosystem + new attackers.
Scans auth.log for (a) known attacker IOCs, (b) brute-force clusters, (c) unexpected successful logins.
Appends JSONL to evidence/<UTC-date>/attackers.jsonl. Designed for cron (*/15). Idempotent via state file."""
import json, re, glob, os, subprocess
from datetime import datetime, timezone
from collections import Counter

HOME = '/root/evez-agentnet'
STATE = f'{HOME}/.state/attacker_watch.json'
KNOWN = {  # May 2026 attack ecosystem IOCs — CIDR: attribution
    '80.94.92.':  'DMZHOST/TECHOFF SRV (AS48090, Luca Palo) — May 22 2026 EVEZ attacker block',
    '2.57.122.':  'PPTECHNOLOGY (Pitzalis) — Metasploit C2 range, WyDOT corridor overlap',
    '45.156.87.': 'VMHeaven/Winter (WorkTitans, AS209847) — 1201 brute-forces on 2026-05-22',
}
BF_THRESHOLD = 10       # failed SSH auths per IP per window = cluster
ACCEPT_BASE = {'104.28.164.133'}  # authorized remote-access sources (Cloudflare front)
LOGS = sorted(glob.glob('/var/log/auth.log*'))

def state(): return json.load(open(STATE)) if os.path.exists(STATE) else {'offsets': {}}
def save(s): os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(s, open(STATE,'w'))

def read_lines(path, off):
    try: sz = os.path.getsize(path)
    except OSError: return [], sz
    if sz < off: off = 0
    with open(path, 'rb') as f:
        f.seek(off); data = f.read()
    return data.decode('utf-8', errors='replace').splitlines(), sz

def main():
    s = state()
    events = []
    for path in LOGS:
        off = s['offsets'].get(path, 0)
        lines, newoff = read_lines(path, off)
        s['offsets'][path] = newoff
        if not lines: continue
        fails = Counter()
        accepts = Counter()
        known_hits = []
        for l in lines:
            m = re.search(r'from ((?:\d{1,3}\.){3}\d{1,3})', l)
            ip = m.group(1) if m else None
            if 'Failed password' in l or 'Invalid user' in l or 'authentication failure' in l:
                if ip: fails[ip] += 1
            if 'Accepted' in l:
                u = re.search(r'for (?:invalid user )?(\S+) from', l)
                accepts[f'{u.group(1) if u else "?"}@{ip}'] += 1
            for pfx, attr in KNOWN.items():
                if ip and ip.startswith(pfx):
                    known_hits.append({'ip': ip, 'line': l[:200], 'attribution': attr})
        for ip, n in fails.items():
            if n >= BF_THRESHOLD:
                events.append({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'bruteforce_cluster',
                               'ip': ip, 'count': n, 'known_ecosystem': any(ip.startswith(p) for p in KNOWN)})
        for k, n in accepts.items():
            ip = k.split('@')[-1]
            if ip not in ACCEPT_BASE and not ip.startswith('100.126.'):
                events.append({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'UNEXPECTED_SUCCESSFUL_LOGIN',
                               'who': k, 'count': n})
        for h in known_hits:
            events.append({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'known_attacker_activity',
                           **h})
    if events:
        d = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        out = f'{HOME}/evidence/{d}/attackers.jsonl'
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'a') as f:
            for e in events: f.write(json.dumps(e) + '\n')
        critical = [e for e in events if e['type'] == 'UNEXPECTED_SUCCESSFUL_LOGIN']
        print(f'{len(events)} events -> {out}' + (' | CRITICAL: unexpected successful login(s)!' if critical else ''))
    else:
        print('clean')
    save(s)

if __name__ == '__main__':
    main()
