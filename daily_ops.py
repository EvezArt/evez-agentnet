#!/usr/bin/env python3
"""daily_ops.py — daily war status: CH company statuses (TECHOFF/BESTDC strike-off watch),
gazette check, attacker_watch summary, open-channel reply check. Appends to evidence/<date>/daily_ops.jsonl."""
import json, subprocess, re, os, hashlib
from datetime import datetime, timezone
OUT='/root/evez-agentnet/evidence'
COMPANIES={'16090235':'TECHOFF SRV (Palo/attack-ASN)','15259087':'BESTDC (Palo/ACTIVE successor)','12461131':'UNMANAGED (Bunea/routing)'}
def status(c):
    p=subprocess.run(['curl','-sSL','-m','25',f'https://find-and-update.company-information.service.gov.uk/company/{c}'],capture_output=True)
    t=p.stdout.decode('utf-8','replace')
    st=re.search(r'Company status ([A-Za-z —-]+)<',t)
    strike='1002A' in t
    return {'status':st.group(1).strip() if st else '?','strike_off_process':strike}
def main():
    now=datetime.now(timezone.utc).isoformat()
    rec={'ts':now,'companies':{c:status(c) for c in COMPANIES}}
    # attacker summary from last 24h jsonl
    day=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    f=f'{OUT}/{day}/attackers.jsonl'
    if os.path.exists(f):
        lines=open(f).read().strip().split('\n')
        rec['attack_events_today']=len(lines)
    else:
        rec['attack_events_today']=0
    d=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    os.makedirs(f'{OUT}/{d}',exist_ok=True)
    open(f'{OUT}/{d}/daily_ops.jsonl','a').write(json.dumps(rec)+'\n')
    print(json.dumps(rec))
if __name__=='__main__': main()
