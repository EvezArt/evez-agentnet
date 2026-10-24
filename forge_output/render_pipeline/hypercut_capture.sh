#!/bin/bash
# hypercut_capture.sh — chrome first, THEN roll camera when screen is lit.
pkill -f 'gc-hyper-prof2' 2>/dev/null
sleep 1
DISPLAY=:99 google-chrome --no-sandbox --disable-gpu --kiosk --no-first-run \
  --no-default-browser-check --window-position=0,0 --window-size=1920,1080 \
  --user-data-dir=/tmp/gc-hyper3 \
  'file:///root/evez-agentnet/forge_output/render_pipeline/three_names_hypercut.html' \
  > /dev/null 2>&1 &
echo 'chrome launching, probing...'
LIT=0
for i in $(seq 1 60); do
  ffmpeg -y -v error -f x11grab -video_size 1920x1080 -framerate 1 -i :99 -frames:v 1 /tmp/probe_frame.png 2>/dev/null
  B=$(python3 -c "
from PIL import Image
import numpy as np
try:
    im = np.asarray(Image.open('/tmp/probe_frame.png').convert('L'), dtype=float)
    print(1 if float((im > 30).mean()) > 0.15 else 0)
except Exception:
    print(0)
")
  if [ "$B" = "1" ]; then echo "SCREEN LIT at probe $i"; LIT=1; break; fi
  sleep 5
done
echo "probe done LIT=$LIT"
if [ "$LIT" = "1" ]; then
  ffmpeg -y -v error -f x11grab -draw_mouse 0 -video_size 1920x1080 -framerate 24 \
    -i :99 -t 55 -pix_fmt yuv420p -c:v libx264 -preset veryfast -crf 23 \
    /root/evez-agentnet/forge_output/render_pipeline/hypercut_raw3.mp4
  echo CAPTURE_DONE
else
  echo SCREEN_NEVER_LIT
fi
