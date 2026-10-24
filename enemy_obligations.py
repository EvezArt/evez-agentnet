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
 {'id':'ch-strikeoff-objection','demand':'CH Dissolution re-replied 2026-10-20 (COH2370479X, ingested evidence/2026-10-24/ch_dissolution_reply_COH2370479X_20261020.txt sha 77b5fb8e): 10-14 consent+evidence submission still NOT registrable — evidence must arrive as ATTACHMENTS (invoices, court documents, correspondence) dated within 6 months naming TECHOFF SRV LIMITED in full; NEW 14-day hold placed 2026-10-20; identity-divulgence consent already on file from the 10-14 submission; attachment-form evidence pack staged forge_output/CH_EVIDENCE_REPLY_READY/ (signed 5-Oct LBA naming TECHOFF + 10-11 objection + abuse-lane correspondence + IS CC-2026-157384 receipt)','served':'2026-10-20','deadline':'2026-11-03','consequence':'hold lapses ~2026-11-03: dissolution resumes and TECHOFF SRV LIMITED is struck off before the claim crystallizes; attachment-form evidence must reach dissobjections@companieshouse.gov.uk before then (email objections close 2026-12-01, online service thereafter); SEND LANE = custodian GO (pack ready, provenance note inside flags the 10-14 inline 52,290/28-Sep-LBA claims that have no on-disk artifact)'},
 {'id':'ch-acsp-review','demand':'CH integrity review of Paramount ACSP co-location','served':'2026-10-05','deadline':'2026-11-04','consequence':'HMRC supervisory referral'},
 {'id':'foipa-1758537-000','demand':'FBI FOIA response (statutory 20 working days from 2026-09-30 ack)','served':'2026-09-30','deadline':'2026-10-28','consequence':'FOIA appeal + congressional inquiry letter'},
 {'id':'ic3-confirmation','demand':'IC3 complaint auto-confirmation','served':'2026-10-01','deadline':'2026-10-31','consequence':'re-file via field office with case cross-ref'},
 {'id':'rfj-weekly-check','demand':'custodian: weekly SecureDrop login (codename account)','served':'2026-10-05','deadline':'weekly/Sunday','consequence':'missed analyst reply window'},
 {'id':'servhost-abuse-demand','demand':'ServHost abuse/preservation demand response (abuse@serv.host, sent 2026-10-11 from victim Gmail)','served':'2026-10-11','deadline':'2026-10-18','consequence':'escalate to upstream transit providers + RIPE NCC abuse + regulator (NIS2/hosting provider duty)','resolved':'2026-10-19','resolution':'deadline expired in 8 days of verified silence; consequence EXECUTED 2026-10-19 02:09-02:22 UTC under custodian GO of 2026-10-17: transit/provider lane (NetShield AS49418, Mevspace AS207208, ADMAN AS57494, FiberState AS26042, Tele Asia cc), RIPE NCC non-compliance lane (abuse@ripe.net, tickets #1124364 + #1124969), ICO NIS2 lane (icocasework@ico.org.uk). Receipts: evidence/2026-10-19/servhost_escalation_sends.json + servhost_escalation_outbound/ + ico_acknowledgment.eml; replies on record: RIPE deflections x2 (64bc777f 10-19, 78ce7ab7 10-20), Prime Telecom AS207957 denial (eb424881), Cardiff ECMS deferral, GoDaddy autoreply. Enemy silence preserved = spoliation inference stands; clock discharged.'},
 {'id':'ch-diabin-complaint','demand':'INTEGRITY COMPLAINT SERVED to enquiries@companieshouse.gov.uk 2026-10-11 (CHSL/NETSHIELD/DPKGSOFT/SERVHOST four-shell nominee network); CH Contact Centre replied 2026-10-12 (ref COH2382672X) with deflection to Action Fraud 0300 123 2040 + Insolvency Service, no integrity review opened; FOLLOW-UPS PER CH GUIDANCE BOTH FILED 2026-10-21 (Insolvency Service CC-2026-157384; HMRC MLRCIT supervision referral re Paramount ACSP, sha 2f49b799)','served':'2026-10-12','deadline':'2026-10-25','consequence':'follow-up per CH guidance: Insolvency Service complaint (gov.uk/complain-company) + HMRC ACSP supervisory referral; legal posture decision = custodian','resolved':'2026-10-23','resolution':'follow-up consequence executed ahead of the 10-25 deadline: Insolvency Service complaint verified on disk (evidence/2026-10-21/insolvency_service_receipt_CC-2026-157384.md, filed 2026-10-21, TECHOFF SRV 16090235 + connected BESTDC/UNMANAGED/SERV.HOST named, cross-refs IC3/FOIPA/CH lanes); HMRC MLRCIT supervision referral recorded in clock snapshots 10-21..10-23 with digest 2f49b799 but no independent receipt artifact located this tick — tracked onward by the hmrc-mlrcit-referral clock (follow-up deadline 11-11) which will surface it if the filing needs repeating. Remaining custodian item = legal posture decision, carried by the downstream clocks, not this deadline. Clock discharged.'},
 {'id':'insolvency-service-complaint','demand':'Insolvency Service company complaint FILED 2026-10-21 ref CC-2026-157384 (TECHOFF SRV 16090235 + connected BESTDC 15259087 / UNMANAGED 12461131 / SERV.HOST 15728390); IS reviews within ~2 months and is confidential','served':'2026-10-21','deadline':'2026-12-21','consequence':'if no acknowledgment received: follow-up with reference CC-2026-157384 citing their 15-working-day customer charter'},
 {'id':'hmrc-mlrcit-referral','demand':'HMRC Economic Crime Supervision (MLRCIT@hmrc.gov.uk) supervision referral re Paramount Company Formations Ltd 01489657 ACSP attestations (35 Firs Ave 61+ companies; PPTECH dissolved 14 days post-verification); 15-working-day SLA','served':'2026-10-21','deadline':'2026-11-11','consequence':'follow-up to MLRCIT + cite in CH ACSP fit-and-proper review (COH2382672X lane)'},
 {'id':'action-fraud-report','demand':'Action Fraud report (COH guidance route, ref COH2382672X lane): box IP Cloudflare-blocked from portal; complete fill guide prepared (forge_output/ACTION_FRAUD_FILL_GUIDE.md) — CUSTODIAN HANDS: portal or 0300 123 2040 from own device','served':'2026-10-21','deadline':'2026-10-25','consequence':'UK criminal-report lane stays unbanked; NFIB reference never cross-refs the IC3/FOIPA/IS chain'},
 {'id':'rfj-tip-upload','demand':'RFJ cyber-program tip (Aeza SDN 54566/54567 continuation + successor shells): submit-ready text verified (forge_output/RFJ_TIP_SUBMIT_READY.md), bundle v3 sha 9f49cbdc intact — CUSTODIAN HANDS ONLY: @RFJ_English from own Telegram/device','served':'2026-10-21','deadline':'2026-10-26','consequence':'reward clock never starts; designation-gap evidence sits unreported while successors re-arm'},
]
def main():
    now=datetime.now(timezone.utc).date()
    recs=[]
    fails=0
    for c in CLOCKS:
        if c.get('resolved'):
            # Consequence executed, receipts archived: the clock is discharged.
            # days_left is emitted as null so downstream consumers (patrol
            # walk_near, dashboards) stop firing an alarm over a consequence
            # we already carried out; the resolution text keeps the provenance.
            recs.append({**c,'days_left':None,'status':'RESOLVED'})
            continue
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
