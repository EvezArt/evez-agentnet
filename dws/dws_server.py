#!/usr/bin/env python3
"""Local-first Digital Weather Station API. Python stdlib only."""
from __future__ import annotations
import csv, hashlib, json, os, statistics, threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(os.environ.get('DWS_DATA_DIR', Path.home() / '.local' / 'share' / 'digital-weather-station')).expanduser()
OBS = ROOT / 'observations.jsonl'
EVENTS = ROOT / 'events.jsonl'
LOCK = threading.Lock()
TOKEN = os.environ.get('DWS_API_TOKEN', '')
HOST = os.environ.get('DWS_HOST', '127.0.0.1')
PORT = int(os.environ.get('DWS_PORT', '8788'))
MAX_BODY = 2_000_000

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def read_jsonl(path):
    if not path.exists(): return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except json.JSONDecodeError: continue
    return out

def append_chain(path, obj):
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK:
        previous = read_jsonl(path)
        prev_hash = previous[-1].get('hash','0'*64) if previous else '0'*64
        record = dict(obj)
        record.setdefault('recorded_at', now())
        record['prev_hash'] = prev_hash
        canonical = json.dumps(record, sort_keys=True, separators=(',',':'), ensure_ascii=False)
        record['hash'] = hashlib.sha256(canonical.encode()).hexdigest()
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
        return record

def parse_timestamp(s):
    try:
        d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    except Exception: return None

def normalize_observation(o):
    ts=parse_timestamp(o.get('timestamp'))
    metric=str(o.get('metric','')).strip()
    try: value=float(o.get('value'))
    except (TypeError,ValueError): value=float('nan')
    if not ts or not metric or len(metric)>100 or not (value==value and abs(value)!=float('inf')):
        raise ValueError('Each observation needs a valid ISO timestamp, metric, and finite numeric value.')
    return {'timestamp':ts,'metric':metric,'value':value,'source':str(o.get('source','agent')).strip()[:200], 'domain':str(o.get('domain','unspecified')).strip()[:100], 'event_id':str(o.get('event_id','')).strip()[:100], 'note':str(o.get('note','')).strip()[:1000]}

def median_mad(vals):
    if not vals: return 0.0,0.0
    med=statistics.median(vals); mad=statistics.median(abs(x-med) for x in vals)
    return med,mad

def analyze(rows):
    groups={}
    for r in rows: groups.setdefault(r['metric'],[]).append(r)
    result=[]
    for metric, rs in sorted(groups.items()):
        vals=[r['value'] for r in rs]; med,mad=median_mad(vals)
        out=[]
        for r in rs:
            if mad > 1e-12: z=.67448975*(r['value']-med)/mad
            else: z=0 if r['value']==med else (float('inf') if r['value']>med else -float('inf'))
            if len(vals)>=7 and abs(z)>=3.5: out.append({**r,'robust_z':z if abs(z)!=float('inf') else ('+inf' if z>0 else '-inf')})
        latest=max(rs,key=lambda r:r['timestamp'])
        result.append({'metric':metric,'count':len(rs),'latest':latest,'median':med,'mad':mad,'outlier_count':len(out),'outliers':out})
    return {'generated_at':now(),'data_origin':'authorized imported observations','records':len(rows),'metrics':result,'interpretation':'Anomaly flags are statistical deviations, not causal diagnoses or evidence of intent.'}

class Handler(BaseHTTPRequestHandler):
    server_version='DigitalWeatherStation/1.0'
    def log_message(self, fmt, *args): print('%s - %s' % (self.address_string(), fmt%args))
    def _json(self, code, obj):
        body=json.dumps(obj, ensure_ascii=False, allow_nan=False, default=str).encode()
        self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def _auth(self):
        if not TOKEN: return True
        return self.headers.get('Authorization','') == 'Bearer '+TOKEN
    def _body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n<1 or n>MAX_BODY: raise ValueError('Body missing or too large (max 2 MB).')
        return json.loads(self.rfile.read(n))
    def do_GET(self):
        if not self._auth(): return self._json(401,{'error':'unauthorized'})
        path=urlparse(self.path).path
        if path=='/health': return self._json(200,{'ok':True,'service':'digital-weather-station','version':'1.0','data_dir':str(ROOT),'auth_enabled':bool(TOKEN),'time':now()})
        rows=read_jsonl(OBS)
        if path=='/observations':
            q=parse_qs(urlparse(self.path).query); metric=q.get('metric',[None])[0]; limit=min(10000,max(1,int(q.get('limit',['1000'])[0])))
            filtered=[r for r in rows if metric is None or r.get('metric')==metric]
            return self._json(200,{'count':len(filtered),'observations':filtered[-limit:]})
        if path=='/analysis': return self._json(200,analyze(rows))
        if path=='/events': return self._json(200,{'count':len(read_jsonl(EVENTS)),'events':read_jsonl(EVENTS)[-1000:]})
        if path=='/': return self._json(200,{'service':'Digital Weather Station API','endpoints':['GET /health','GET /observations','POST /observations','GET /analysis','GET /events','POST /events']})
        return self._json(404,{'error':'not found'})
    def do_POST(self):
        if not self._auth(): return self._json(401,{'error':'unauthorized'})
        path=urlparse(self.path).path
        try: data=self._body()
        except Exception as e: return self._json(400,{'error':str(e)})
        if path=='/observations':
            items=data if isinstance(data,list) else data.get('observations') if isinstance(data,dict) else None
            if not isinstance(items,list) or not items or len(items)>5000: return self._json(400,{'error':'Send a non-empty observation array (max 5000 records).'} )
            try: norm=[normalize_observation(x) for x in items]
            except Exception as e: return self._json(422,{'error':str(e)})
            saved=[append_chain(OBS,x) for x in norm]
            return self._json(201,{'accepted':len(saved),'first_hash':saved[0]['hash'],'last_hash':saved[-1]['hash']})
        if path=='/events':
            if not isinstance(data,dict) or not str(data.get('title','')).strip(): return self._json(422,{'error':'Event title is required.'})
            typ=str(data.get('type','observation'))
            if typ not in ('observation','hypothesis','intervention','context','correction'): return self._json(422,{'error':'Unsupported event type.'})
            ev={'timestamp':parse_timestamp(data.get('timestamp') or now()),'type':typ,'title':str(data['title']).strip()[:200],'detail':str(data.get('detail','')).strip()[:4000],'source':str(data.get('source','agent')).strip()[:200]}
            if not ev['timestamp']: return self._json(422,{'error':'Invalid timestamp.'})
            saved=append_chain(EVENTS,ev); return self._json(201,saved)
        return self._json(404,{'error':'not found'})

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    if HOST not in ('127.0.0.1','localhost','::1') and not TOKEN:
        raise SystemExit('Refusing non-loopback bind without DWS_API_TOKEN. Set a strong token or bind to 127.0.0.1.')
    httpd=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f'Digital Weather Station API listening at http://{HOST}:{PORT} (auth={bool(TOKEN)}; data={ROOT})')
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()
if __name__=='__main__': main()
