#!/usr/bin/env python3
"""Tiny offline ChatGPT-style runtime for Termux/low-resource Android.

Architecture:
  browser -> stdlib HTTP server -> local llama.cpp server (optional)
                              -> deterministic fallback when no model exists
                              -> append-only local conversation record
                              -> optional EVEZ Event Spine presentation witness

Canonical conversation records remain unwatermarked. Presentation responses
receive a visible device-local watermark plus a hash that points back to the
canonical content. When the daemon package is available, that presentation
relationship is also committed to the same hash-chained Event Spine.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from watermark import present

# Keep the offline runtime standalone, while allowing a repository checkout to
# use the canonical daemon Event Spine for presentation witnesses.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from daemon.spine import append_presentation, verify_chain
except Exception:  # pragma: no cover - standalone Termux copies need no daemon.
    append_presentation = None
    verify_chain = None

ROOT = pathlib.Path(os.environ.get("EVEZ_OFFLINE_HOME", "~/.evez-offline")).expanduser()
ROOT.mkdir(parents=True, exist_ok=True)
CHAT_LOG = ROOT / "chat.jsonl"
HOST = os.environ.get("EVEZ_OFFLINE_HOST", "127.0.0.1")
PORT = int(os.environ.get("EVEZ_OFFLINE_PORT", "8787"))
LLAMA_URL = os.environ.get("EVEZ_LLAMA_URL", "http://127.0.0.1:8080")
MODEL_NAME = os.environ.get("EVEZ_MODEL", "local-gguf")
DEVICE_LABEL = os.environ.get("EVEZ_DEVICE_LABEL", "EVEZ-POCKET")


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


def status() -> dict:
    spine_state = "UNAVAILABLE"
    spine_head = None
    spine_events = None
    if verify_chain is not None:
        try:
            valid, checked, head = verify_chain()
            spine_state = "VERIFIED" if valid else "CONTRADICTED"
            spine_head = head
            spine_events = checked
        except Exception as exc:
            spine_state = f"ERROR:{type(exc).__name__}"

    return {
        "offline": True,
        "model_server": LLAMA_URL,
        "model": MODEL_NAME,
        "history_file": str(CHAT_LOG),
        "history_messages": len(recent_messages(100000)),
        "presentation_watermark": True,
        "device_label": DEVICE_LABEL,
        "event_spine": spine_state,
        "event_spine_events": spine_events,
        "event_spine_head": spine_head,
    }


def export_history() -> str:
    if not CHAT_LOG.exists():
        return "No local conversation history."
    return CHAT_LOG.read_text(encoding="utf-8")


def verify_history() -> dict:
    checked = 0
    if not CHAT_LOG.exists():
        history = {"valid": True, "records_checked": 0, "path": str(CHAT_LOG)}
    else:
        with CHAT_LOG.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    return {
                        "valid": False,
                        "records_checked": checked,
                        "path": str(CHAT_LOG),
                        "reason": "invalid JSON",
                    }
                if not isinstance(event, dict) or "ts" not in event or "kind" not in event or "data" not in event:
                    return {
                        "valid": False,
                        "records_checked": checked,
                        "path": str(CHAT_LOG),
                        "reason": "invalid record shape",
                    }
                checked += 1
        history = {"valid": True, "records_checked": checked, "path": str(CHAT_LOG)}

    if verify_chain is not None:
        try:
            valid, events, head = verify_chain()
            history["event_spine"] = {
                "valid": valid,
                "events_checked": events,
                "head": head,
            }
        except Exception as exc:
            history["event_spine"] = {
                "valid": False,
                "reason": f"{type(exc).__name__}: {exc}",
            }
    else:
        history["event_spine"] = {"available": False}

    return history


def answer(user_text: str) -> str:
    command = user_text.strip().lower()
    if command == "/status":
        return json.dumps(status(), indent=2)
    if command == "/verify":
        return json.dumps(verify_history(), indent=2)
    if command == "/history":
        return "\n".join(
            f"{m['role']}: {m['content']}"
            for m in recent_messages(50)
        )
    if command == "/help":
        return (
            "Commands: /status, /history, /verify, /help. "
            "Normal messages go to the local model."
        )

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
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#171b1b">
<title>EVEZ Offline</title>
<style>
:root{color-scheme:dark}
body{margin:0;background:#171b1b;color:#d7dfdc;font:16px system-ui,sans-serif}
main{width:100%;max-width:760px;margin:auto;min-height:100vh;display:flex;flex-direction:column;box-sizing:border-box}
header{padding:14px 16px;border-bottom:1px solid #35403e;font-weight:700;position:sticky;top:0;background:#171b1b;z-index:2}
#log{flex:1;padding:16px 12px 92px;overflow:auto}
.msg{white-space:pre-wrap;margin:0 0 14px;padding:11px 13px;border-radius:9px;overflow-wrap:anywhere}
.u{background:#26302e}.a{background:#202625}
.wm{margin-top:8px;padding-top:7px;border-top:1px solid #35403e;font-size:11px;line-height:1.35;opacity:.68;letter-spacing:.02em}
form{display:flex;padding:10px;gap:8px;border-top:1px solid #35403e;position:fixed;left:0;right:0;bottom:0;background:#171b1b}
form textarea{flex:1;min-width:0;background:#202625;color:#d7dfdc;border:1px solid #46524f;border-radius:8px;padding:10px;resize:none}
button{background:#31403d;color:#d7dfdc;border:1px solid #52615d;border-radius:8px;padding:0 16px}
@media (min-width:761px){form{left:50%;right:auto;width:760px;transform:translateX(-50%);box-sizing:border-box}}
</style>
<main><header>EVEZ OFFLINE · local runtime · no cloud</header><section id="log"></section>
<form><textarea id="q" rows="2" placeholder="Message or /status"></textarea><button>Send</button></form></main>
<script>
const log=document.querySelector('#log'),q=document.querySelector('#q');
function add(c,t){let d=document.createElement('div');d.className='msg '+c;d.textContent=t;log.append(d);log.scrollTop=log.scrollHeight}
document.querySelector('form').onsubmit=async e=>{
 e.preventDefault();let t=q.value.trim();if(!t)return;q.value='';add('u',t);add('a','…');
 let box=log.lastChild;
 try{
  let r=await fetch('/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:t})});
  let j=await r.json();
  if(j.error){box.textContent='Runtime error: '+j.error;return}
  box.textContent=j.answer;
  let wm=document.createElement('div');wm.className='wm';wm.textContent=j.watermark.text;box.append(wm);
 }catch(x){box.textContent='Runtime error: '+x}
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
            self.send_json({
                "ok": True,
                "offline": True,
                "model_server": LLAMA_URL,
                "presentation_watermark": True,
                "event_spine": append_presentation is not None,
            })
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
            canonical = answer(text)
            presentation, watermark = present(canonical)

            if append_presentation is not None:
                append_presentation(
                    artifact_hash=str(watermark["artifact_hash"]),
                    watermark_id=str(watermark["watermark_id"]),
                    device=str(watermark["device"]),
                    source=str(watermark["source"]),
                    association=str(watermark["association"]),
                )

            self.send_json({
                "answer": canonical,
                "presentation": presentation,
                "watermark": watermark,
            })
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print(f"EVEZ Offline: http://{HOST}:{PORT}")
    print(f"Conversation log: {CHAT_LOG}")
    print(f"Event spine: {'available' if append_presentation is not None else 'standalone'}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
