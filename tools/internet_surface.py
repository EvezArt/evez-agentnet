#!/usr/bin/env python3
"""Bounded Internet Surface Engine for EVEZ.

This is not unrestricted Internet control. It performs authorized,
read-oriented observations of public HTTP(S) surfaces and emits
append-only evidence records. It respects robots.txt, redirect limits,
response-size limits, rate limits, and explicit domain allowlists.
"""
from __future__ import annotations
import argparse, hashlib, json, re, time
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import urllib.robotparser
import httpx

UA = "EVEZ-Reality-Surface/1.0 (+https://evez.art/; bounded observer)"

def now(): return datetime.now(timezone.utc).isoformat()
def sha256(b): return hashlib.sha256(b).hexdigest()

def allowed(url, domains):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    host = p.hostname.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)

def robots_ok(url, client):
    p = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(f"{p.scheme}://{p.netloc}", "/robots.txt"))
    try:
        r = client.get(rp.url, timeout=10, follow_redirects=True)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        return rp.can_fetch(UA, url), rp.url, r.status_code
    except Exception as e:
        return False, rp.url, f"error:{type(e).__name__}"

def observe(url, domains, max_bytes, timeout, max_redirects):
    if not allowed(url, domains):
        return {"state":"blocked","reason":"domain_not_allowlisted","uri":url,"observed_at":now()}
    limits = httpx.Limits(max_connections=4, max_keepalive_connections=2)
    with httpx.Client(headers={"User-Agent":UA,"Accept":"text/html,application/json,text/plain,*/*"},
                      follow_redirects=True, max_redirects=max_redirects, limits=limits) as c:
        ok, robots_url, robots_status = robots_ok(url, c)
        if not ok:
            return {"state":"blocked","reason":"robots_denied_or_unavailable","uri":url,
                    "robots_url":robots_url,"robots_status":robots_status,"observed_at":now()}
        r = c.get(url, timeout=timeout)
        body = r.content[:max_bytes]
        ctype = r.headers.get("content-type","").lower()
        rep = "json" if "json" in ctype else "html" if "html" in ctype else "text"
        return {"state":"observed","uri":str(r.url),"requested_uri":url,
                "representation":rep,"status_code":r.status_code,
                "content_type":ctype,"content_length":len(r.content),
                "truncated":len(r.content)>max_bytes,"content_hash":sha256(body) if len(r.content) <= max_bytes else None,
                "prefix_hash":sha256(body) if len(r.content) > max_bytes else None,
                "hash_scope":"full" if len(r.content) <= max_bytes else "prefix",
                "observed_at":now(),"auth_boundary":"public",
                "robots_url":robots_url,"robots_status":robots_status}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("urls",nargs="+")
    ap.add_argument("--domain",action="append",required=True,dest="domains")
    ap.add_argument("--out",default="docs/reality-observations.jsonl")
    ap.add_argument("--max-bytes",type=int,default=1048576)
    ap.add_argument("--timeout",type=float,default=15)
    ap.add_argument("--max-redirects",type=int,default=5)
    ap.add_argument("--delay",type=float,default=1.0)
    a=ap.parse_args()
    with open(a.out,"a",encoding="utf-8") as f:
        for i,u in enumerate(a.urls):
            rec=observe(u,a.domains,a.max_bytes,a.timeout,a.max_redirects)
            rec["id"]="surface_"+sha256((u+"|"+rec["observed_at"]).encode())[:16]
            rec["evidence_type"]="runtime_http_observation"
            f.write(json.dumps(rec,separators=(",",":"))+"\n"); f.flush()
            print(json.dumps(rec,separators=(",",":")))
            if i+1<len(a.urls): time.sleep(max(0,a.delay))

if __name__=="__main__": main()
