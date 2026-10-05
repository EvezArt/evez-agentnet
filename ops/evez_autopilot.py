#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

OWNER = os.getenv('EVEZ_GITHUB_OWNER', 'EvezArt')
ROOT = Path(os.getenv('EVEZ_ROOT', Path.cwd())).resolve()
STATE = ROOT / 'data' / 'evez-autopilot'
LEDGER = STATE / 'events.jsonl'
QUEUE = STATE / 'queue'
MAX_REPOS = int(os.getenv('EVEZ_MAX_REPOS', '300'))
CYCLE_SECONDS = int(os.getenv('EVEZ_CYCLE_SECONDS', '1800'))

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def canon(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def h(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()

def run(cmd, *, cwd=None, stdin=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd or ROOT, input=stdin, text=True, capture_output=True, timeout=timeout)

def github_get(path):
    req = Request('https://api.github.com' + path, headers={
        'Accept':'application/vnd.github+json',
        'User-Agent':'EVEZ-Autopilot',
        'X-GitHub-Api-Version':'2022-11-28',
    })
    token = os.getenv('GITHUB_TOKEN')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return 0, {'error': str(e)}

def repo_inventory():
    repos=[]
    for page in range(1, 10):
        status, data = github_get(f'/users/{OWNER}/repos?type=owner&per_page=100&page={page}')
        if status != 200 or not isinstance(data,list):
            return {'status':status,'repos':repos}
        repos.extend([
            {k:r.get(k) for k in ('name','full_name','private','fork','archived','default_branch','size','stargazers_count','forks_count','open_issues_count','language','license','created_at','updated_at','pushed_at','html_url')}
            for r in data if not r.get('private',False)
        ])
        if len(data)<100 or len(repos)>=MAX_REPOS:
            break
    return {'status':200,'repos':repos[:MAX_REPOS]}

def prior_hash():
    if not LEDGER.exists(): return '0'*64
    last=''
    for line in LEDGER.read_text(encoding='utf-8',errors='replace').splitlines():
        if line.strip(): last=line
    if not last: return '0'*64
    try: return json.loads(last).get('hash','0'*64)
    except Exception: return '0'*64

def append_event(event_type, payload, status='SUPPORTED'):
    STATE.mkdir(parents=True,exist_ok=True)
    body={'schema':'evez.autopilot.event.v1','event_type':event_type,'status':status,'observed_at':now(),'payload':payload,'parent_hash':prior_hash()}
    body['hash']=h(body)
    with LEDGER.open('a',encoding='utf-8') as f:
        f.write(canon(body)+'\n')
    return body['hash']

def exposure_summary():
    p=ROOT/'PUBLIC_EXPOSURE_AUDIT.md'
    if not p.exists(): return {'present':False}
    text=p.read_text(encoding='utf-8',errors='replace')
    # Deliberately keep only headings and non-secret summary lines.
    wanted=[]
    for line in text.splitlines():
        if line.startswith('## FINDING') or line.startswith('**Actions:**') or line.startswith('## Recommended order') or line.startswith('**Total live-shaped credentials found:'):
            wanted.append(line.strip())
    return {'present':True,'headings':wanted[:40],'source':str(p)}

def build_packet(snapshot):
    repos=snapshot['repos']
    active=[r for r in repos if not r.get('archived')]
    archived=[r for r in repos if r.get('archived')]
    mirrors=[r for r in repos if r.get('name') in ('evez-ai','evez-atlas','evez-os','evez-agentnet')]
    return {
      'source':'PUBLIC GITHUB OBSERVATION',
      'owner':OWNER,
      'observed_at':now(),
      'repo_count':len(repos),
      'active_count':len(active),
      'archived_count':len(archived),
      'largest_repos':sorted(({'name':r['name'],'size':r.get('size'),'archived':r.get('archived')} for r in repos),key=lambda x:x.get('size') or 0,reverse=True)[:20],
      'recent_repos':sorted(({'name':r['name'],'pushed_at':r.get('pushed_at'),'url':r.get('html_url')} for r in repos),key=lambda x:x.get('pushed_at') or '',reverse=True)[:30],
      'focus_repos':mirrors,
      'exposure':exposure_summary(),
      'doctrine':['CLAIMED != MEASURED != REPLICATED != EXPLAINED','PROVENANCE != TRUTH'],
    }

def hermes(prompt):
    cmd=shutil.which('hermes-agent')
    if not cmd: cmd=shutil.which('hermes')
    if not cmd: return {'status':'UNAVAILABLE','output':'Hermes command not found'}
    if Path(cmd).name=='hermes-agent':
        args=[cmd,'--query-file','-','--oneshot','--quiet']
    else:
        args=[cmd,'chat','--query-file','-','--oneshot','--quiet']
    try:
        p=subprocess.run(args,input=prompt,text=True,capture_output=True,timeout=900,cwd=ROOT)
        return {'status':'OK' if p.returncode==0 else 'ERROR','returncode':p.returncode,'output':p.stdout[-30000:],'stderr':p.stderr[-5000:]}
    except Exception as e:
        return {'status':'ERROR','output':str(e)}

def write_queue(packet, hermes_result):
    QUEUE.mkdir(parents=True,exist_ok=True)
    tasks=[
      {'action':'AUDIT_REPOSITORY_GRAPH','risk':'LOW','repo':'EvezArt/evez-ai','instructions':'Map nested evez-ecosystem/evezart-repos mirrors to canonical public repositories. Do not delete or push.'},
      {'action':'AUDIT_SECURITY_EXPOSURE','risk':'LOW','repo':'EvezArt/evez-agentnet','instructions':'Run the public exposure scanner and produce a redacted finding report. Never print secret values.'},
      {'action':'AUDIT_STALE_STATUS','risk':'LOW','repo':'EvezArt/evez-os','instructions':'Identify stale live-status and quantitative claims. Do not rewrite history.'},
      {'action':'PREPARE_VENV_CLEANUP','risk':'MEDIUM','repo':'EvezArt/evez-liminal','instructions':'Create a local patch that removes committed .venv from tracking and preserves .gitignore. Do not push.'},
      {'action':'VERIFY_HERMES_OPENCLAW','risk':'LOW','repo':str(ROOT),'instructions':'Verify hermes-agent and openclaw CLI versions and save only non-secret health facts.'},
    ]
    payload={'created_at':now(),'packet':packet,'hermes':{'status':hermes_result.get('status'),'output':hermes_result.get('output','')},'tasks':tasks}
    path=QUEUE/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return path

def openclaw(task_file):
    if os.getenv('EVEZ_OPENCLAW_EXEC','0')!='1': return {'status':'DISABLED'}
    cmd=shutil.which('openclaw')
    if not cmd: return {'status':'UNAVAILABLE'}
    prompt=('Read this task file. Work only in an isolated/local worktree. '+
            'Perform only LOW-risk investigation or prepare a MEDIUM-risk patch. '+
            'Do not delete remote data, rotate secrets, merge, deploy, or push. '+
            'Write results to data/evez-autopilot/results and return a concise evidence summary.\n\n'+
            str(task_file))
    p=run([cmd,'agent','exec',prompt,'--cwd',str(ROOT),'--json'],timeout=1800)
    return {'status':'OK' if p.returncode==0 else 'ERROR','returncode':p.returncode,'stdout':p.stdout[-20000:],'stderr':p.stderr[-5000:]}

def cycle():
    snapshot=repo_inventory()
    packet=build_packet(snapshot)
    event=append_event('GITHUB_OBSERVATION',packet,'SUPPORTED' if snapshot['status']==200 else 'UNKNOWN')
    prompt='''You are Hermes, the reasoning layer of EVEZ. You are receiving a redacted, public-source observation packet. Analyze it as an evidence reviewer. Do not invent facts. Identify contradictions, stale claims, duplication, security exposure classes, and the three highest-value next probes. Return concise actions with evidence references. Never request or echo credential values.\n\nPACKET:\n''' + json.dumps(packet,ensure_ascii=False)
    hr=hermes(prompt)
    append_event('HERMES_ANALYSIS',{'event_ref':event,'status':hr.get('status'),'output':hr.get('output','')[:30000]},'SUPPORTED' if hr.get('status')=='OK' else 'UNKNOWN')
    q=write_queue(packet,hr)
    oc=openclaw(q)
    append_event('OPENCLAW_RESULT',{'queue':str(q),'status':oc.get('status'),'stdout':oc.get('stdout','')[-12000:]},'SUPPORTED' if oc.get('status')=='OK' else 'UNKNOWN')
    (STATE/'latest.json').write_text(json.dumps({'packet':packet,'hermes':hr,'openclaw':oc,'queue':str(q),'generated_at':now()},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'ok':True,'repos':len(snapshot['repos']),'hermes':hr.get('status'),'openclaw':oc.get('status'),'queue':str(q),'event':event},indent=2))

def main():
    once='--once' in sys.argv
    while True:
        cycle()
        if once: return
        time.sleep(CYCLE_SECONDS)

if __name__=='__main__': main()