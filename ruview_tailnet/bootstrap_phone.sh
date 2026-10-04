#!/data/data/com.termux/files/usr/bin/bash
# RuView phone bootstrap — ONE paste, run in Termux on the Android phone.
#
#   bash -c "$(curl -fsSL http://100.126.180.47:8099/bootstrap.sh)"
#
# It installs the relay, registers this phone's LAN IP with the server so the
# ESP32 target is known without anyone retyping it, and starts forwarding.
#
# Android note: the Tailscale Android app already holds the VPN slot, so this
# does NOT install or run tailscale in Termux. Nothing to configure there.
set -euo pipefail

SERVER="${RUVIEW_SERVER:-100.126.180.47}"
BOOT_PORT="${RUVIEW_BOOT_PORT:-8099}"
BASE="http://$SERVER:$BOOT_PORT"
DIR="$HOME/ruview"
API_TOKEN="${RUVIEW_API_TOKEN:-}"

say() { echo "==> $*"; }
die() { echo "!! $*" >&2; exit 1; }

say "preflight"
command -v curl >/dev/null || { pkg install -y curl; }
command -v python >/dev/null || pkg install -y python
echo "    ok"

# Verify the tailnet path before touching anything.
say "checking the tailnet path to $SERVER"
if ! curl -fsS --max-time 10 -H "Authorization: Bearer $API_TOKEN" "$BASE/health" >/dev/null; then
  die "cannot reach $BASE over Tailscale. Check the Tailscale app is signed in on this phone."
fi
echo "    ok"

say "installing the relay"
mkdir -p "$DIR"
curl -fsSL -H "Authorization: Bearer $API_TOKEN" "$BASE/ruview_relay.py" -o "$DIR/ruview_relay.py"
chmod +x "$DIR/ruview_relay.py"
python -c "import ast,sys; ast.parse(open('$DIR/ruview_relay.py').read())" \
  || die "downloaded relay does not parse — refusing to install it"
echo "    ok ($DIR/ruview_relay.py)"

# The ESP32 must target this phone's LAN address on the sensing WiFi. It is a
# private address the server cannot discover on its own, so report it.
say "reporting this phone's LAN address"
LAN_IP="$(ip -4 addr show wlan0 2>/dev/null | awk '/inet /{split($2,a,"/"); print a[1]; exit}')"
TS_IP="$(ip -4 addr show 2>/dev/null | awk '/inet /{split($2,a,"/"); if (a[1] ~ /^100\./) {print a[1]; exit}}')"
if [ -z "$LAN_IP" ]; then
  echo "    WARNING: no wlan0 address found. Is this phone on the sensing WiFi?"
else
  curl -fsS -X POST -H "Authorization: Bearer $API_TOKEN" -H 'Content-Type: application/json' \
    -d "{\"lan_ip\":\"$LAN_IP\",\"hostname\":\"$(hostname)\",\"tailscale_ip\":\"$TS_IP\"}" \
    "$BASE/register" && echo
  echo "    ESP32 must target: $LAN_IP:5005"
fi

say "starting the relay"
# Detach so the relay survives this shell. termux-wake-lock keeps Android from
# killing it while the screen is off.
termux-wake-lock 2>/dev/null || true
nohup python "$DIR/ruview_relay.py" --relay --server "$SERVER" --bind 0.0.0.0:5005 \
  > "$DIR/relay.log" 2>&1 &
echo "    pid $!  (log: $DIR/relay.log)"
sleep 2

say "verifying"
python "$DIR/ruview_relay.py" --server "$SERVER" --status || true

cat <<EOF

The phone side is done. To keep it alive across reboots, run the relay from
Termux:Boot or tmux:
  tmux new -s ruview
  $DIR/ruview_relay.py --relay --server $SERVER --bind 0.0.0.0:5005
  (detach with Ctrl-b d)

Server-side ESP32 target is recorded. Flash the node with:
  CONFIG_CSI_TARGET_ADDR="$LAN_IP"
  CONFIG_CSI_TARGET_PORT=5005
EOF
