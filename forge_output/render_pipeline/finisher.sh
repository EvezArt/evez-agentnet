#!/bin/bash
# finisher.sh — waits for fix_pass + micro_chunk to exit, then runs the
# comedy bank and the final assembly gate. The episode completes itself.
H=/root/evez-agentnet/forge_output/render_pipeline
PY=/root/evez-media-venv/bin/python3
cd /root/evez-davinci

while pgrep -f '[f]ix_pass.py' > /dev/null; do sleep 30; done
echo "=== fix pass exited $(date -u +%FT%TZ) ==="
while pgrep -f '[m]icro_chunk.py' > /dev/null; do sleep 30; done
echo "=== micro pass exited $(date -u +%FT%TZ) ==="

echo "=== comedy bank resume ==="
$PY $H/comedy_bank_render.py
echo "=== comedy done $(date -u +%FT%TZ) count=$(ls $H/../comedy_bank/ | wc -l) ==="

echo "=== final assembly + gate ==="
$PY $H/doc_assemble.py
RC=$?
echo "=== ENDGAME DONE rc=$RC $(date -u +%FT%TZ) ==="
