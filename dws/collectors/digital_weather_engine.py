#!/usr/bin/env python3
"""Tokenless public-source collector + digital-weather measurement matrix. Python stdlib only."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, statistics, time, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(os.environ.get('DWS_DATA_DIR', Path.home()/'.local/share/digital-weather-station')).expanduser()
UA='DigitalWeatherStation/1.0 (public-data research; contact: local-operator)'
# Explicit allowlist: public feeds only, no credentials or private endpoints.
SOURCES={
 'NOAA_SWPC_ALERTS': {'url':'https://www.swpc.noaa.gov/products/alerts-watches-and-warnings.rss','kind':'rss','domain':'space_weather'},
 'USGS_EARTHQUAKES': {'url':'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson','kind':'json','domain':'physical_events'},
 'NASA_EONET': {'url':'https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100','kind':'json','domain':'physical_events'},
 'CISA_CYBER_ALERTS': {'url':'https://www.cisa.gov/cybersecurity-advisories/all.xml','kind':'rss','domain':'cybersecurity'},
 'GITHUB_STATUS': {'url':'https://www.githubstatus.com/history.rss','kind':'rss','domain':'internet_services'},
}

def utcnow(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def digest(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def fetch(url, timeout=15, max_bytes=4_000_000):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname: raise ValueError('Only HTTPS sources are allowed')
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/atom+xml, application/json, application/xml, text/xml;q=0.9, */*;q=0.5'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        data=r.read(max_bytes+1)
        if len(data)>max_bytes: raise ValueError('Response exceeds size limit')
        return data.decode('utf-8','replace'),r.headers.get('Content-Type','')

def text_of(node): return ' '.join(''.join(node.itertext()).split())[:2000]
def parse_source(name, cfg, body):
    out=[]; url=cfg['url']; domain=cfg['domain']; now=utcnow()
    if cfg['kind']=='json':
        data=json.loads(body)
        if name=='USGS_EARTHQUAKES':
            for f in data.get('features',[]):
                p=f.get('properties',{}); ts=p.get('time')
                stamp=datetime.fromtimestamp(ts/1000,timezone.utc).isoformat().replace('+00:00','Z') if ts else now
                out.append({'timestamp':stamp,'metric':'event_count','value':1,'source':name,'domain':domain,'event_id':str(f.get('id','')),'note':f"magnitude={p.get('mag')} place={p.get('place','')}"[:1000], 'source_url':p.get('url',url)})
                if isinstance(p.get('mag'),(int,float)): out.append({'timestamp':stamp,'metric':'event_magnitude','value':float(p['mag']),'source':name,'domain':domain,'event_id':str(f.get('id','')),'note':str(p.get('place',''))[:500],'source_url':p.get('url',url)})
        elif name=='NASA_EONET':
            for e in data.get('events',[]):
                dates=[x.get('date') for x in e.get('geometry',[]) if x.get('date')]
                stamp=dates[-1] if dates else now
                out.append({'timestamp':stamp,'metric':'event_count','value':1,'source':name,'domain':domain,'event_id':str(e.get('id','')),'note':(e.get('title','')+' categories='+','.join(c.get('title','') for c in e.get('categories',[])))[:1000],'source_url':e.get('link',url)})
    else:
        root=ET.fromstring(body)
        for item in root.findall('.//item'):
            title=text_of(item.find('title')) if item.find('title') is not None else 'untitled'
            link=text_of(item.find('link')) if item.find('link') is not None else url
            pub=text_of(item.find('pubDate')) if item.find('pubDate') is not None else now
            try: stamp=parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
            except Exception: stamp=now
            guid=text_of(item.find('guid')) if item.find('guid') is not None else link
            out.append({'timestamp':stamp,'metric':'published_item_count','value':1,'source':name,'domain':domain,'event_id':guid[:200],'note':title[:1000],'source_url':link})
    return out

def append_chain(path, record):
    path.parent.mkdir(parents=True,exist_ok=True); prev='0'*64
    if path.exists():
        try: prev=json.loads(path.read_text(encoding='utf-8').splitlines()[-1]).get('hash',prev)
        except Exception: pass
    record={**record,'recorded_at':utcnow(),'prev_hash':prev}; record['hash']=digest(record)
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
    return record

def collect_once():
    observations=[]; sources=[]; events_path=ROOT/'events.jsonl'
    for name,cfg in SOURCES.items():
        started=time.time()
        try:
            body,ctype=fetch(cfg['url']); rows=parse_source(name,cfg,body)
            # content fingerprint retained without copying whole page into logs
            fp=hashlib.sha256(body.encode()).hexdigest(); observations.extend(rows)
            status={'source':name,'url':cfg['url'],'status':'ok','http_content_type':ctype,'item_count':len(rows),'content_sha256':fp,'duration_ms':round((time.time()-started)*1000,1),'collected_at':utcnow()}
        except Exception as e:
            status={'source':name,'url':cfg['url'],'status':'error','error_type':type(e).__name__,'error':str(e)[:300],'collected_at':utcnow()}
        sources.append(status); append_chain(events_path,{'event_type':'SOURCE_SCAN','payload':status})
        time.sleep(1.0) # conservative, sequential polling
    ROOT.mkdir(parents=True,exist_ok=True)
    obs_path=ROOT/'observations.jsonl'; existing=set()
    if obs_path.exists():
        for line in obs_path.read_text(encoding='utf-8').splitlines():
            try:
                r=json.loads(line); existing.add((r.get('source'),r.get('event_id'),r.get('metric'),r.get('timestamp')))
            except Exception: pass
    added=0
    for row in observations:
        key=(row.get('source'),row.get('event_id'),row.get('metric'),row.get('timestamp'))
        if key in existing: continue
        append_chain(obs_path,{'event_type':'OBSERVATION','payload':row}); added+=1; existing.add(key)
    report={'collected_at':utcnow(),'sources':sources,'parsed_rows':len(observations),'new_observations':added,'storage':str(ROOT),'note':'Public anonymous sources only; source failures are recorded, not silently treated as zero activity.'}
    append_chain(events_path,{'event_type':'COLLECTION_CYCLE','payload':report})
    (ROOT/'latest_collection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def load_obs():
    path=ROOT/'observations.jsonl'; rows=[]
    if not path.exists(): return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            rec=json.loads(line); p=rec.get('payload',{})
            if rec.get('event_type')=='OBSERVATION' and isinstance(p.get('value'),(int,float)): rows.append(p)
        except Exception: pass
    return rows

def pearson(xs,ys):
    if len(xs)<4:return None
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys); dx=[x-mx for x in xs]; dy=[y-my for y in ys]
    den=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return sum(x*y for x,y in zip(dx,dy))/den if den else None

def matrix_report(rows):
    by={}
    for r in rows: by.setdefault(r['metric'],[]).append(r)
    metrics=sorted(by); summaries={};
    for m,rs in by.items():
        vals=[float(x['value']) for x in rs]; med=statistics.median(vals); mad=statistics.median(abs(v-med) for v in vals)
        latest=max(rs,key=lambda x:x['timestamp'])
        anomalies=[]
        for r in rs:
            z=(0.67448975*(float(r['value'])-med)/mad) if mad>1e-12 else (0.0 if float(r['value'])==med else math.copysign(float('inf'), float(r['value'])-med))
            if len(vals)>=7 and abs(z)>=3.5: anomalies.append({'timestamp':r['timestamp'],'value':r['value'],'robust_z':(round(z,3) if math.isfinite(z) else ('+inf' if z>0 else '-inf')),'source':r.get('source'),'note':r.get('note','')})
        summaries[m]={'n':len(vals),'latest':latest,'median':med,'mad':mad,'anomalies':anomalies}
    corr={};
    # Pairwise correlations only on exact shared timestamps; no interpolation.
    for i,a in enumerate(metrics):
        for b in metrics[i+1:]:
            aa={r['timestamp']:float(r['value']) for r in by[a]}; bb={r['timestamp']:float(r['value']) for r in by[b]}; common=sorted(set(aa)&set(bb))
            # pearson() returns None on degenerate (zero-variance) series; guard the round, not just the sample count
            r_val=pearson([aa[t] for t in common],[bb[t] for t in common]) if len(common)>=4 else None
            corr[f'{a}__{b}']={'n_aligned':len(common),'pearson_r':round(r_val,5) if (r_val is not None and math.isfinite(r_val)) else None,'interpretation':'Exploratory association only; shared timestamps and sufficient sample count required.'}
    return {'generated_at':utcnow(),'observations':len(rows),'metrics':summaries,'correlation_matrix':corr,'caveats':['Different source cadences make many pairs unaligned.','RSS publication counts are not measures of total public attention.','No individual-level tracking is performed.','Correlation is not causation; confounding and source-selection bias remain.']}

def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('collect',help='Scan allowlisted public sources once, anonymously')
    sub.add_parser('matrix',help='Compute robust anomaly and correlation matrices from collected observations')
    sub.add_parser('run',help='Collect then calculate matrices')
    loop=sub.add_parser('loop',help='Repeat collection at a conservative interval'); loop.add_argument('--minutes',type=float,default=60); loop.add_argument('--once',action='store_true')
    sub.add_parser('verify-ledger',help='Verify the hash chain in local event ledger')
    args=ap.parse_args()
    if args.cmd in ('collect','run','loop'):
        while True:
            report=collect_once(); print(json.dumps(report,indent=2))
            if args.cmd=='run':
                matrix=matrix_report(load_obs()); (ROOT/'latest_matrix.json').write_text(json.dumps(matrix,indent=2),encoding='utf-8'); print(json.dumps({'matrix_file':str(ROOT/'latest_matrix.json'),'metrics':len(matrix['metrics']),'pairs':len(matrix['correlation_matrix'])},indent=2)); break
            if args.cmd=='collect' or (args.cmd=='loop' and args.once): break
            time.sleep(max(5,args.minutes*60))
    elif args.cmd=='matrix':
        report=matrix_report(load_obs()); ROOT.mkdir(parents=True,exist_ok=True); (ROOT/'latest_matrix.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
    elif args.cmd=='verify-ledger':
        path=ROOT/'events.jsonl'; prev='0'*64; checked=0
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                r=json.loads(line); claimed=r.pop('hash',None)
                if r.get('prev_hash')!=prev or digest(r)!=claimed: raise SystemExit(f'INTEGRITY FAILURE at record {checked+1}')
                prev=claimed; checked+=1
        print(json.dumps({'valid':True,'records_checked':checked,'head':prev}))
if __name__=='__main__': main()
