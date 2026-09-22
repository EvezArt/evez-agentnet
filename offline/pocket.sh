#!/data/data/com.termux/files/usr/bin/bash
set -eu

ROOT="$HOME/.evez-offline"
MODEL="${EVEZ_MODEL_PATH:-$ROOT/models/qwen2.5-0.5b-instruct-q3_k_m.gguf}"

echo "EVEZ POCKET"
echo "==========="
echo "1. Install local runtime + model"
echo "2. Start chat"
echo "3. Stop model"
echo "4. Health check"

read -r -p "Select [1-4]: " choice

case "$choice" in
  1)
    bash "$(dirname "$0")/setup-termux.sh"
    ;;
  2)
    bash "$(dirname "$0")/run-termux.sh"
    ;;
  3)
    bash "$(dirname "$0")/stop-termux.sh"
    ;;
  4)
    if curl -fsS http://127.0.0.1:8787/health; then
      echo
      echo "EVEZ Pocket is running."
    else
      echo "EVEZ Pocket is not running."
      exit 1
    fi
    ;;
  *)
    echo "Unknown selection."
    exit 2
    ;;
esac
