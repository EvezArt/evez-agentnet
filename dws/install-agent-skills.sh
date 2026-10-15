#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_SKILLS="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}"
HERMES_SKILLS="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}"
mkdir -p "$OPENCLAW_SKILLS/digital-weather-station" "$HERMES_SKILLS/digital-weather-station"
cp "$ROOT/skills/openclaw-digital-weather/SKILL.md" "$OPENCLAW_SKILLS/digital-weather-station/SKILL.md"
cp "$ROOT/skills/hermes-digital-weather/SKILL.md" "$HERMES_SKILLS/digital-weather-station/SKILL.md"
printf 'Installed OpenClaw skill: %s\nInstalled Hermes skill:   %s\n' "$OPENCLAW_SKILLS/digital-weather-station/SKILL.md" "$HERMES_SKILLS/digital-weather-station/SKILL.md"
printf '\nAPI defaults to http://127.0.0.1:8788 on the same host. If agents run elsewhere or in containers, set DWS_URL to a private reachable address and enable DWS_API_TOKEN.\n'
