#!/usr/bin/env python3
"""enemy_obligations.py — holds the ATTACKERS to the obligations WE served them.
Tracks every demand clock we opened; screams (exit 2, fails loudly) when they blow one.
Cron daily. Appends to evidence/<date>/enemy_clocks.jsonl."""
import json, os
from datetime import datetime, timezone, date

HOME='/root/evez-agentnet'
STATE=f'{HOME}/.state/enemy_obligations.json'
# obligation: id, demand, served, deadline, consequence-if-blown
CLOCKS=[
 {'id':'bunea-14day-payment','demand':'USD 25,000 compensation + written cease/desist undertaking (letter before action, Bunea/UNMANAGED)','served':'2026-10-06','deadline':'2026-10-20','consequence':'issue E&W proceedings, claim costs + interest'},
 {'id':'palo-14day-payment','demand':'USD 25,000 + cessation + preservation (formal victim notice, dmzhostabuse@gmail.com)','served':'2026-10-06','deadline':'2026-10-20','consequence':'aggravated §1030 posture; civil co-defendant'},
 {'id':'buneatelecom-preservation','demand':'preservation of transit/customer records (abuse@bunea.eu)','served':'2026-10-06','deadline':'ongoing','consequence':'spoliation inference in all forums'},
 {'id':'godaddy-preservation','demand':'domain + WHOIS/payment data preservation','served':'2026-10-05','deadline':'ongoing','consequence':'regulator escalation'},
 {'id':'namecheap-preservation','demand':'registration/privacy/payment preservation','served':'2026-10-05','deadline':'ongoing','consequence':'ICANN WHOIS inaccuracy complaint'},
 {'id':'cloudflare-preservation','demand':'zone/account data preservation','served':'2026-10-05','deadline':'ongoing','consequence':'litigation hold cited in claim'},
 {'id':'ch-strikeoff-objection','demand':'Companies House: record creditor objection, suspend strike-off TECHOFF 16090235','served':'2026-10-05','deadline':'2026-10-19','consequence':'escalate to CH objections team + MP letter'},
 {'id':'ch-acsp-review','demand':'CH integrity review of Paramount ACSP co-location','served':'2026-10-05','deadline':'2026-11-04','consequence':'HMRC supervisory referral'},
 {'id':'foipa-1758537-000','demand':'FBI FOIA response (statutory 20 working days from 2026-09-30 ack)','served':'2026-09-30','deadline':'2026-10-28','consequence':'FOIA appeal + congressional inquiry letter'},
 {'id':'ic3-confirmation','demand':'IC3 complaint auto-confirmation','served':'2026-10-01','deadline':'2026-10-31','consequence':'re-file via field office with case cross-ref'},
 {'id':'rfj-weekly-check','demand':'custodian: weekly SecureDrop login (codename account)','served':'2026-10-05','deadline':'weekly/Sunday','consequence':'missed analyst reply window'},
]
def main():
    now=datetime.now(timezone.utc).date()
    recs=[]
    fails=0
    for c in CLOCKS:
        dl=date.fromisoformat(c['deadline']) if len(c['deadline'])==10 else None
        days=(dl-now).days if dl else None
        blown = days is not None and days<0
        status='BLOWN' if blown else ('DUE' if days is not None and days<=3 else 'running' if dl else 'ongoing')
        if blown: fails+=1
        recs.append({**c,'days_left':days,'status':status})
    d=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    os.makedirs(f'{HOME}/evidence/{d}',exist_ok=True)
    with open(f'{HOME}/evidence/{d}/enemy_clocks.jsonl','a') as f:
        f.write(json.dumps({'ts':datetime.now(timezone.utc).isoformat(),'clocks':recs})+'\n')
    for r in recs:
        print(f"[{r['status']:>7}] {r['days_left'] if r['days_left'] is not None else '∞':>3}d  {r['id']}: {r['demand'][:70]}")
    if fails:
        print(f'\n{fails} ENEMY DEADLINE(S) BLOWN — consequence stage armed.')
        raise SystemExit(2)
if __name__=='__main__': main()
