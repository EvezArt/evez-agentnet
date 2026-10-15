# Agent skills

Both folders contain Agent Skills-format `SKILL.md` instructions for the same API:

- `openclaw-digital-weather/SKILL.md` — install as an OpenClaw workspace skill.
- `hermes-digital-weather/SKILL.md` — install as a Hermes skill.

The skill instructions do not grant API access by themselves. The agent runtime must have HTTP or shell/curl access to the host running `dws_server.py`, and must be configured with `DWS_URL` and (if enabled) `DWS_API_TOKEN`. If agents run in containers, `127.0.0.1` refers to the container itself; use a reachable private interface/Tailscale address and token authentication instead.
