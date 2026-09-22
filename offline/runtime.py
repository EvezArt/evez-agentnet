#!/usr/bin/env python3
"""Tiny offline ChatGPT-style runtime for Termux/low-resource Android.

Architecture:
  browser -> stdlib HTTP server -> local llama.cpp server (optional)
                              -> deterministic fallback when no model exists
                              -> append-only local conversation spine

No cloud API is required. No Python packages are required.
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(os.environ.get("EVEZ_OFFLINE_HOME", "~/.evez-offline")).expanduser()
ROOT.mkdir(parents=True, exist_ok=True)
CHAT_LOG = ROOT / "chat.jsonl"
HOST = os.environ.get("EVEZ_OFFLINE_HOST", "127.0.0.1")
PORT = int(os.environ.get("EVEZ_OFFLINE_PORT", "8787"))
LLAMA_URL = os.environ.get("EVEZ_LLAMA_URL", "http://127.0.0.1:8080")
MODEL_NAME = os.environ.get("EVEZ_MODEL", "local-gguf")


def append(kind: str, data: dict) -> None:
    event = {"ts": time.time(), "kind": kind, "data": data}
    with CHAT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def recent_messages(limit: int = 12) -> list[dict]:
    if not CHAT_LOG.exists():
        return []
    rows = []
    for line in CHAT_LOG.read_text(encoding="utf-8").splitlines()[-200:]:
        try:
            event = json.loads(line)
            if event["kind"] == "message":
                rows.append(event["data"])
        except Exception:
            continue
    return rows[-limit:]


def local_completion(messages: list[dict], max_tokens: int = 384) -> str | None:
    payload = json.dumps({
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        LLAMA_URL.rstrip("/") + "/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read())
        return body["choices"][0]["message"]["content"]
    except Exception:
        return None


def fallback(text: str) -> str:
    return (
        "OFFLINE FALLBACK\n\n"
        "No local language model is running. Your message was recorded locally.\n"
        f"Input: {text[:1200]}\n\n"
        "Start a local llama.cpp-compatible server and retry for actual generation."
    )


def answer(user_text: str) -> str:
    history = recent_messages()
    system = {
        "role": "system",
        "content": (
            "You are EVEZ Offline, a compact local assistant. "
            "Prefer factual, concise answers. Mark unknown claims UNKNOWN. "
            "Do not invent access to the internet or hidden state."
        ),
    }
    messages = [system] + history + [{"role": "user", "content": user_text}]
    append("message", {"role": "user", "content": user_text})
    result = local_completion(messages)
    if result is None:
        result = fallback(user_text)
    append("message", {"role": "assistant", "content": result})
    return result


HTML = r"""<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EVEZ Offline</title>
<style>
body{margin:0;background:#171b1b;color:#d7dfdc;font:16px system-ui,sans-serif}
main{max-width:760px;margin:auto;min-height:100vh;display:flex;flex-direction:column}
header{padding:14px 16px;border-bottom:1px solid #35403e;font-weight:700}
#log{flex:1;padding:16px;overflow:auto}
.msg{white-space:pre-wrap;margin:0 0 14px;padding:11px 13px;border-radius:9px}
.u{background:#26302e}.a{background:#202625}
form{display:flex;padding:10px;gap:8px;border-top:1px solid #35403e;position:sticky;bottom:0;background:#171b1b}
textarea{flex:1;background:#202625;color:#d7dfdc;border:1px solid #46524f;border-radius:8px;padding:10px;resize:none}
button{background:#31403d;color:#d7dfdc;border:1px solid #52615d;border-radius:8px;padding:0 16px}
</style>
<main><header>EVEZ OFFLINE · local runtime</header><section id="log"></section>
<form><textarea id="q" rows="2" placeholder="Message..."></textarea><button>Send</button></form></main>
<script>
const log=document.querySelector('#log'),q=document.querySelector('#q');
function add(c,t){let d=document.createElement('div');d.className='msg '+c;d.textContent=t;log.append(d);log.scrollTop=log.scrollHeight}
document.querySelector('form').onsubmit=async e=>{
 e.preventDefault();let t=q.value.trim();if(!t)return;q.value='';add('u',t);add('a','…');
 let box=log.lastChild;
 try{let r=await fetch('/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:t})});
 let j=await r.json();box.textContent=j.answer}catch(x){box.textContent='Runtime error: '+x}
};
</script>
"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj: dict, status: int = 200) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self.send_json({"ok": True, "offline": True, "model_server": LLAMA_URL})
            return
        raw = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/chat":
            self.send_json({"error": "not found"}, 404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n))
            text = str(body.get("message", "")).strip()
            if not text or len(text) > 12000:
                raise ValueError("message must contain 1..12000 characters")
            self.send_json({"answer": answer(text)})
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print(f"EVEZ Offline: http://{HOST}:{PORT}")
    print(f"Conversation log: {CHAT_LOG}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
