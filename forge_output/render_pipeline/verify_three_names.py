#!/usr/bin/env python3
"""Verify + finalize THE THREE NAMES screen recording."""
import subprocess, os
import numpy as np
from PIL import Image

S = "/root/evez-agentnet/forge_output/render_pipeline"
RAW = f"{S}/three_names_raw.mp4"
# boot lead ~3-4s (chrome launch), film 95s
OUT = "/root/evez-agentnet/forge_output/films/the_three_names.mp4"

subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "4", "-i", RAW,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], check=True)
d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", OUT],
                   capture_output=True, text=True).stdout
print("duration:", [l for l in d.splitlines() if l.startswith("duration")][0])

# frame-truth at key acts (trimmed time = film time)
CHECKS = [(6, "cards", "bright"), (26, "law", "green"), (52, "rite", "accent"),
          (68, "night eyes", "green"), (90, "end card", "violet")]
for ft, label, expect in CHECKS:
    p = f"/tmp/tn_{ft}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT, "-ss", str(ft),
                    "-frames:v", "1", p], check=True)
    im = np.asarray(Image.open(p).convert("RGB"), dtype=int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    bright = float((im.min(axis=2) > 200).mean())
    green = float(((g > 180) & (r < 120) & (g > b + 60)).mean())
    red = float(((r > 180) & (g < 140) & (b < 140)).mean())
    violet = float(((r > 120) & (b > 180) & (g < 140)).mean())
    ok = {"bright": bright > 0.001, "green": green > 0.001, "accent": (red + violet) > 0.00002}[expect]
    print(f"t={ft} {'PASS' if ok else 'FAIL'} [{label}] bright={bright:.4f} green={green:.4f} red={red:.5f} violet={violet:.5f}")
    os.remove(p)
print("size:", os.path.getsize(OUT) // 1024, "KB")
