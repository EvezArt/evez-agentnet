#!/usr/bin/env bash
# Read-only diagnostics for the EVEZ phone -> tailnet -> relay -> agents -> RuView mesh.
# Never prints response bodies, environment values, tokens, or full service configuration.
set -u

RUVIEW_URL="${EVEZ_RUVIEW_URL:-https://vmi3544756.mooneye-shade.ts.net}"
TIMEOUT="${EVEZ_DIAG_TIMEOUT:-4}"

rows="$(mktemp)"
trap 'rm -f "$rows"' EXIT
emit() { printf '{"check":"%s","status":"%s","detail":"%s"}\n' "$1" "$2" "$3" >>"$rows"; }

probe_http() {
  local name="$1" url="$2" code
  if ! command -v curl >/dev/null 2>&1; then
    emit "$name" "unknown" "curl-not-installed"
    return
  fi
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" "$url" 2>/dev/null || true)"
  case "$code" in
    2??) emit "$name" "ok" "http-$code" ;;
    3??) emit "$name" "degraded" "http-$code-redirect" ;;
    401|403) emit "$name" "reachable-auth-required" "http-$code" ;;
    502|503|504) emit "$name" "upstream-error" "http-$code" ;;
    000|"") emit "$name" "unreachable" "no-http-response" ;;
    *) emit "$name" "degraded" "http-$code" ;;
  esac
}

check_command() {
  local name="$1"; shift
  if ! command -v "$1" >/dev/null 2>&1; then
    emit "$name" "unknown" "$1-not-installed"
    return
  fi
  if "$@" >/dev/null 2>&1; then
    emit "$name" "ok" "command-succeeded"
  else
    emit "$name" "degraded" "command-failed-or-not-authorized"
  fi
}

check_port() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "([.:])${port}$"; then
      emit "tcp-${port}" "listening" "local-tcp-listener-present"
    else
      emit "tcp-${port}" "not-listening" "no-local-tcp-listener"
    fi
  else
    emit "tcp-${port}" "unknown" "ss-not-installed"
  fi
}

check_udp() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    if ss -lun 2>/dev/null | awk '{print $4}' | grep -Eq "([.:])${port}$"; then
      emit "udp-${port}" "listening" "local-udp-listener-present"
    else
      emit "udp-${port}" "not-listening" "no-local-udp-listener"
    fi
  else
    emit "udp-${port}" "unknown" "ss-not-installed"
  fi
}

check_command "tailscale-status" tailscale status
check_command "tailscale-serve" tailscale serve status
probe_http "ruview-remote-health" "${RUVIEW_URL%/}/health"
probe_http "ruview-remote-nodes" "${RUVIEW_URL%/}/api/v1/nodes"

for port in 3000 3001 8787 8788 18789 18790; do
  check_port "$port"
done
check_udp 5005

if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -qi ruview; then
    emit "docker-ruview" "running" "matching-container-visible"
  else
    emit "docker-ruview" "unknown" "no-running-container-name-matched-ruview"
  fi
else
  emit "docker-ruview" "unknown" "docker-not-installed"
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"suite":"evez-mesh-doctor","mode":"read-only","error":"python3-not-installed"}'
  exit 2
fi
python3 - "$rows" <<'PY'
import json, pathlib, sys
items = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text().splitlines() if line.strip()]
print(json.dumps({"suite":"evez-mesh-doctor","mode":"read-only","checks":items}, separators=(",", ":"), sort_keys=True))
PY
