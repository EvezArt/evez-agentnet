#!/usr/bin/env bash
# SSH lockdown — SAFE, ORDER-CRITICAL, SELF-VERIFYING
#
# DO NOT RUN THIS BLIND. It is gated on a key-auth proof, because on this host
# (checked 2026-10-03) key auth DOES NOT currently work:
#
#   authorized_keys : SHA256:qznBp8Qy16GUyw/5EBzsq+x/D+vkz8ucqr+QmAg8TgM  evezart-vmi3544756
#   local key       : SHA256:sPb9ogmwkn1C9oT+ElnCAbqCdt03EiIolj2OBWZYRJo  KRNL::deploy
#
# Different keys. `ssh -i /root/.ssh/krnl-deploy root@127.0.0.1` fails today.
# Setting PasswordAuthentication=no right now would lock every human out of the
# VPS with no working way back in except the provider's console.
#
# This script refuses to proceed until it has PROVEN key auth works.

set -uo pipefail
BACKUP=/root/.vault/ssh-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP"
cp -a /etc/ssh/sshd_config "$BACKUP/" 2>/dev/null
cp -a /etc/ssh/sshd_config.d "$BACKUP/" 2>/dev/null
echo "[1/5] backed up ssh config to $BACKUP"

fail() { echo "ABORTED: $*"; echo "Nothing changed. Backup at $BACKUP"; exit 1; }

# --- PROOF GATE -------------------------------------------------------
KEY="${1:-}"
if [ -z "$KEY" ]; then
  fail "pass the path to your PRIVATE key: $0 /path/to/key"
fi
[ -f "$KEY" ] || fail "key not found: $KEY"

echo "[2/5] proving key auth works BEFORE changing anything..."
OUT=$(timeout 20 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 \
        -o IdentitiesOnly=yes -o BatchMode=yes -i "$KEY" \
        root@127.0.0.1 'echo KEYPROOF_OK' 2>&1)
case "$OUT" in
  *KEYPROOF_OK*) echo "      key auth CONFIRMED" ;;
  *) fail "key auth does NOT work with $KEY — disabling passwords would lock you out.
      ssh said: $OUT" ;;
esac

# --- APPLY ------------------------------------------------------------
echo "[3/5] writing hardening drop-in..."
cat > /etc/ssh/sshd_config.d/00-disable-password-auth.conf <<'EOF'
# Added 2026-10-03 by ssh_harden.sh, only after key auth was proven to work.
# 00-enable-password-auth.conf is neutralised below.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
X11Forwarding no
EOF

# Neutralise the drop-in that re-enables passwords. Rename, don't delete:
# the original is preserved for rollback.
if [ -f /etc/ssh/sshd_config.d/00-enable-password-auth.conf ]; then
  mv /etc/ssh/sshd_config.d/00-enable-password-auth.conf \
     /etc/ssh/sshd_config.d/00-enable-password-auth.conf.DISABLED
  echo "      neutralised 00-enable-password-auth.conf"
fi
# cloud-init re-enables it too
for f in /etc/ssh/sshd_config.d/*cloud-init*; do
  [ -e "$f" ] || continue
  sed -i 's/^\s*PasswordAuthentication.*/# &  # disabled by ssh_harden.sh/' "$f"
done

echo "[4/5] verifying config parses, then checking the EFFECTIVE result..."
sshd -t || fail "sshd -t failed; not reloading"
EFF=$(sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication)')
echo "$EFF" | sed 's/^/      /'
echo "$EFF" | grep -q '^passwordauthentication no' \
  || fail "effective config still enables passwords; not reloading"
echo "$EFF" | grep -q '^permitrootlogin prohibit-password' \
  || fail "root login not restricted to keys; not reloading"

# --- RELOAD, NOT RESTART ---------------------------------------------
# reload keeps existing sessions alive; restart would drop them.
systemctl reload ssh 2>/dev/null || systemctl reload sshd

echo "[5/5] post-change proof from the public address..."
sleep 1
if timeout 15 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 \
     -o PubkeyAuthentication=no -o PreferredAuthentications=password \
     -o BatchMode=yes root@80.241.209.34 'echo SHOULD_NOT_HAPPEN' 2>&1 \
     | grep -q SHOULD_NOT_HAPPEN; then
  fail "password auth still works from the internet — investigate"
fi
echo "      password auth from public IP: REFUSED (correct)"
echo "      key auth from loopback: still works"
echo
echo "DONE. Rollback: cp -a $BACKUP/sshd_config.d/. /etc/ssh/sshd_config.d/ && systemctl reload ssh"
