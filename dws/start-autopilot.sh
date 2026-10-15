#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DWS_DATA_DIR:-$HOME/.local/share/digital-weather-station}"
mkdir -p "$DATA_DIR"
PIDFILE="$DATA_DIR/collector.pid"
LOGFILE="$DATA_DIR/collector.log"
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Collector already running (PID $(cat "$PIDFILE"))"; exit 0
fi
nohup env DWS_DATA_DIR="$DATA_DIR" python3 "$ROOT/collectors/digital_weather_engine.py" loop --minutes "${DWS_INTERVAL_MINUTES:-60}" >>"$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "Started tokenless public-source collector PID $(cat "$PIDFILE")"
echo "Data: $DATA_DIR"
echo "Log:  $LOGFILE"
echo "Stop: kill $(cat "$PIDFILE")"
