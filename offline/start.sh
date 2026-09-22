#!/data/data/com.termux/files/usr/bin/bash
set -eu
ROOT="$HOME/.evez-offline"
mkdir -p "$ROOT"
export EVEZ_OFFLINE_HOME="$ROOT"
export EVEZ_OFFLINE_HOST="127.0.0.1"
export EVEZ_OFFLINE_PORT="${EVEZ_OFFLINE_PORT:-8787}"
cd "$(dirname "$0")"
exec python3 runtime.py
