#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$HOME/.evez-offline"
MODEL="${EVEZ_MODEL_PATH:-$ROOT/models/qwen2.5-0.5b-instruct-q3_k_m.gguf}"
LOG="$ROOT/llama.log"
PID="$ROOT/llama.pid"

if ! command -v llama-server >/dev/null 2>&1; then
  echo "llama-server not found. Run: bash offline/setup-termux.sh"
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "model not found: $MODEL"
  echo "Run: bash offline/setup-termux.sh"
  exit 1
fi

mkdir -p "$ROOT"

if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  echo "[EVEZ] local model server already running"
else
  echo "[EVEZ] starting local model on 127.0.0.1:8080"
  nohup llama-server \
    -m "$MODEL" \
    -c 2048 \
    -t 4 \
    --host 127.0.0.1 \
    --port 8080 \
    --parallel 1 \
    >"$LOG" 2>&1 &
  echo $! > "$PID"
fi

sleep 2
export EVEZ_OFFLINE_HOME="$ROOT"
export EVEZ_LLAMA_URL="http://127.0.0.1:8080"
export EVEZ_MODEL="qwen2.5-0.5b-instruct-q3_k_m"
export EVEZ_OFFLINE_HOST="127.0.0.1"
export EVEZ_OFFLINE_PORT="8787"

echo "[EVEZ] starting chat runtime"
echo "[EVEZ] open http://127.0.0.1:8787"
exec python3 "$(dirname "$0")/runtime.py"
