# SKILL.md — EVEZ Plugin Manifest v2
id: evez-agentnet
name: EVEZ AgentNet
version: 1.0.0
schema: 2

runtime:
  port: 8001
  base_url: http://localhost:8001
  health_endpoint: /health
  skills_endpoint: /skills

capabilities:
  - dispatch_task
  - agent_status
  - spawn_child
  - agent_list

fire_events:
  - FIRE_PLUGIN_ACTIVATED
  - FIRE_PLUGIN_DEACTIVATED
  - FIRE_PLUGIN_ERROR
  - FIRE_TASK_DISPATCHED
  - FIRE_TASK_COMPLETE
  - FIRE_AGENT_SPAWNED
  - FIRE_AGENT_DISSOLVED

dependencies:
  - evez-os

auth:
  type: api_key
  header: X-EVEZ-API-KEY

termux:
  start_cmd: "python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001"
  pm2_name: evez-agentnet
