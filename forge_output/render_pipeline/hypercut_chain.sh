#!/bin/bash
# hypercut_chain.sh — wait for the voices, then assemble + seal + ship note.
while ! grep -q 'HYPERCUT VOICES DONE' /root/evez-agentnet/forge_output/render_pipeline/hypervoices.log; do
  sleep 20
done
echo "voices done — assembling $(date -u +%FT%TZ)"
/root/evez-media-venv/bin/python3 /root/evez-agentnet/forge_output/render_pipeline/assemble_hypercut.py
echo "HYPERCUT CHAIN COMPLETE $(date -u +%FT%TZ)"
