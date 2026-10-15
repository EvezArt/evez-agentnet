#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_SKILLS="${OPENCLAW_SKILLS_DIR:-$HOME/.openclaw/workspace/skills}"
HERMES_SKILLS="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}"
mkdir -p "$OPENCLAW_SKILLS/digital-weather-station" "$HERMES_SKILLS/digital-weather-station"
cp "$ROOT/skills/openclaw/SKILL.md" "$OPENCLAW_SKILLS/digital-weather-station/SKILL.md"
cp "$ROOT/skills/hermes/SKILL.md" "$HERMES_SKILLS/digital-weather-station/SKILL.md"
printf 'Installed OpenClaw skill: %s\nInstalled Hermes skill:   %s\n' "$OPENCLAW_SKILLS/digital-weather-station/SKILL.md" "$HERMES_SKILLS/digital-weather-station/SKILL.md"
printf '\nNo API keys or private credentials are required for the included public feeds.\n'
