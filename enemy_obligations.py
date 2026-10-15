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
 {'id':'ch-strikeoff-objection','demand':'CH Dissolution Section replied 2026-10-14 (ref COH2370479X): objection NOT registrable without documentary evidence of active debt pursuit naming TECHOFF SRV LIMITED (full name incl Limited, dated within 6 months); objector identity-divulgence consent requested; 14-day dissolution hold placed 2026-10-14','served':'2026-10-14','deadline':'2026-10-28','consequence':'hold lapses 2026-10-28: dissolution resumes and TECHOFF SRV LIMITED is struck off before the claim crystallizes; evidence + consent must reach CH Dissolution Section first (email objections close 2026-12-01, online service thereafter)'},
 {'id':'ch-acsp-review','demand':'CH integrity review of Paramount ACSP co-location','served':'2026-10-05','deadline':'2026-11-04','consequence':'HMRC supervisory referral'},
 {'id':'foipa-1758537-000','demand':'FBI FOIA response (statutory 20 working days from 2026-09-30 ack)','served':'2026-09-30','deadline':'2026-10-28','consequence':'FOIA appeal + congressional inquiry letter'},
 {'id':'ic3-confirmation','demand':'IC3 complaint auto-confirmation','served':'2026-10-01','deadline':'2026-10-31','consequence':'re-file via field office with case cross-ref'},
 {'id':'rfj-weekly-check','demand':'custodian: weekly SecureDrop login (codename account)','served':'2026-10-05','deadline':'weekly/Sunday','consequence':'missed analyst reply window'},
 {'id':'servhost-abuse-demand','demand':'ServHost abuse/preservation demand response (abuse@serv.host, sent 2026-10-11 from victim Gmail)','served':'2026-10-11','deadline':'2026-10-18','consequence':'escalate to upstream transit providers + RIPE NCC abuse + regulator (NIS2/hosting provider duty)'},
 {'id':'ch-diabin-complaint','demand':'INTEGRITY COMPLAINT SERVED to enquiries@companieshouse.gov.uk 2026-10-11 (CHSL/NETSHIELD/DPKGSOFT/SERVHOST four-shell nominee network); CH Contact Centre replied 2026-10-12 (ref COH2382672X) with deflection to Action Fraud 0300 123 2040 + Insolvency Service, no integrity review opened','served':'2026-10-12','deadline':'2026-10-25','consequence':'follow-up per CH guidance: Insolvency Service complaint (gov.uk/complain-company) + HMRC ACSP supervisory referral; legal posture decision = custodian'},
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
