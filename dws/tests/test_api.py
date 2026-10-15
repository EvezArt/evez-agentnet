import json, os, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class APITest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
 _s=socket.socket(); _s.bind(('127.0.0.1',0)); self.port=_s.getsockname()[1]; _s.close()  # 18789 is the EVEZ gateway organ on this host; bind ephemeral instead
  env=os.environ.copy(); env.update(DWS_DATA_DIR=self.tmp.name,DWS_HOST='127.0.0.1',DWS_PORT=str(self.port),DWS_API_TOKEN='test-token')
  self.p=subprocess.Popen([sys.executable,str(ROOT/'dws_server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.base=f'http://127.0.0.1:{self.port}'
  for _ in range(40):
   try: self.req('/health'); break
   except Exception: time.sleep(.1)
 def tearDown(self): self.p.terminate(); self.p.wait(timeout=3); self.tmp.cleanup()
 def req(self,path,method='GET',body=None,auth=True):
  data=None if body is None else json.dumps(body).encode(); headers={}
  if data is not None: headers['Content-Type']='application/json'
  if auth: headers['Authorization']='Bearer test-token'
  req=urllib.request.Request(self.base+path,data=data,headers=headers,method=method)
  with urllib.request.urlopen(req,timeout=2) as r: return r.status,json.loads(r.read())
 def test_auth_required(self):
  with self.assertRaises(urllib.error.HTTPError) as e: self.req('/health',auth=False)
  self.assertEqual(e.exception.code,401)
 def test_observations_and_analysis(self):
  rows=[{'timestamp':f'2026-10-10T{h:02d}:00:00Z','metric':'requests','value':100 if h<9 else 1000,'source':'test'} for h in range(10)]
  status,data=self.req('/observations','POST',{'observations':rows}); self.assertEqual(status,201); self.assertEqual(data['accepted'],10)
  _,analysis=self.req('/analysis'); self.assertEqual(analysis['records'],10); self.assertEqual(analysis['metrics'][0]['metric'],'requests'); self.assertGreaterEqual(analysis['metrics'][0]['outlier_count'],1)
 def test_event_hash_chain(self):
  _,one=self.req('/events','POST',{'type':'hypothesis','title':'test hypothesis','detail':'falsifiable'})
  _,two=self.req('/events','POST',{'type':'correction','title':'correction'})
  self.assertEqual(two['prev_hash'],one['hash'])
 def test_invalid_observation(self):
  with self.assertRaises(urllib.error.HTTPError) as e: self.req('/observations','POST',{'observations':[{'timestamp':'bad','metric':'x','value':1}]})
  self.assertEqual(e.exception.code,422)
if __name__=='__main__': unittest.main()
