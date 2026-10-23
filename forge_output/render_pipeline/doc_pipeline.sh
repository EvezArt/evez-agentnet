#!/bin/bash
# doc_pipeline.sh — the full episode pipeline, sequential, storm-proof.
# Launched detached by doc_pipeline_launch.sh; logs to pipeline.log.
set +e
PY=/root/evez-media-venv/bin/python3
SCR=/root/evez-agentnet/forge_output/render_pipeline
cd /root/evez-davinci

echo "=== PIPELINE START $(date -u +%FT%TZ) ==="
echo "--- episode segments (resume) ---"
$PY $SCR/doc_render_v3.py
echo "--- fix pass (resume) ---"
$PY $SCR/fix_pass.py
echo "--- comedy bank (resume) ---"
$PY $SCR/comedy_bank_render.py
echo "--- final assembly + gate ---"
$PY $SCR/doc_assemble.py
echo "=== PIPELINE END $(date -u +%FT%TZ) exit=$? ==="
