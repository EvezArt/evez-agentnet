#!/data/data/com.termux/files/usr/bin/bash
set -eu
ROOT="$HOME/.evez-offline"
PID="$ROOT/llama.pid"
if [ -f "$PID" ]; then
  P="$(cat "$PID")"
  kill "$P" 2>/dev/null || true
  rm -f "$PID"
  echo "[EVEZ] local model stopped"
else
  echo "[EVEZ] no recorded model process"
fi
