#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}")")" && pwd)"
SOURCE="$ROOT/skills/evez-mycelium/SKILL.md"
HERMES_SKILLS="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}"
OPENCLAW_SKILLS="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}"
OVERWRITE="${EVEZ_INSTALL_OVERWRITE:-0}"

if [[ ! -f "$SOURCE" ]]; then
  printf 'Missing source skill: %s\n' "$SOURCE" >&2
  exit 1
fi

install_one() {
  local target_dir="$1"
  local target="$target_dir/evez-mycelium/SKILL.md"

  mkdir -p "$target_dir/evez-mycelium"
  if [[ -f "$target" ]]; then
    if cmp -s "$SOURCE" "$target"; then
      printf 'Already current: %s\n' "$target"
      return 0
    fi
    if [[ "$OVERWRITE" != "1" ]]; then
      printf 'Refusing to overwrite a different skill file: %s\n' "$target" >&2
      printf 'Back it up and rerun with EVEZ_INSTALL_OVERWRITE=1 to replace it.\n' >&2
      return 1
    fi
    cp -p "$target" "$target.bak"
  fi

  install -m 0644 "$SOURCE" "$target"
  printf 'Installed: %s\n' "$target"
}

install_one "$HERMES_SKILLS"
install_one "$OPENCLAW_SKILLS"

printf '\nEVEZ MYCELIUM skill installed in both configured skill directories.\n'
printf 'Reload Hermes/OpenClaw if the new skill is not discovered automatically.\n'
printf 'This installs instructions only; it does not grant credentials or tool permissions.\n'
