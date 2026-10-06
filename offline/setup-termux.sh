#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$HOME/.evez-offline"
MODEL_DIR="$ROOT/models"
MODEL="$MODEL_DIR/qwen2.5-0.5b-instruct-q3_k_m.gguf"
URL="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q3_k_m.gguf?download=true"

echo "[EVEZ] checking Termux packages"
pkg update -y
pkg install -y python llama-cpp curl

mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL" ]; then
  echo "[EVEZ] downloading one compact local model (~432 MB)"
  curl -L --fail --retry 3 -o "$MODEL.part" "$URL"
  mv "$MODEL.part" "$MODEL"
else
  echo "[EVEZ] model already present"
fi

cat > "$ROOT/env.sh" <<EOF
export EVEZ_OFFLINE_HOME="$ROOT"
export EVEZ_MODEL="qwen2.5-0.5b-instruct-q3_k_m"
export EVEZ_LLAMA_URL="http://127.0.0.1:8080"
export EVEZ_OFFLINE_HOST="127.0.0.1"
export EVEZ_OFFLINE_PORT="8787"
export EVEZ_MODEL_PATH="$MODEL"
EOF

echo
echo "[EVEZ] installed."
echo "[EVEZ] model: $MODEL"
echo "[EVEZ] next: bash offline/run-termux.sh"
