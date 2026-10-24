#!/usr/bin/env python3
"""Re-verify THE THREE NAMES with corrected 5s lead offset + fixed key map."""
import subprocess, os
import numpy as np
from PIL import Image

S = "/root/evez-agentnet/forge_output/render_pipeline"
RAW = f"{S}/three_names_raw.mp4"
OUT = "/root/evez-agentnet/forge_output/films/the_three_names.mp4"

subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "5", "-i", RAW,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], check=True)
d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", OUT],
                   capture_output=True, text=True).stdout
print("duration:", [l for l in d.splitlines() if l.startswith("duration")][0])

CHECKS = [
    (16, "three cards", lambda s: s["bright"] > 0.001 and s["green"] > 0.0005),
    (26, "the law", lambda s: s["green"] > 0.001),
    (53, "rite canon", lambda s: s["red"] > 0.00002 or s["violet"] > 0.00002),
    (68, "night eyes", lambda s: s["green"] > 0.001),
    (90, "end card", lambda s: s["violet"] > 0.00002 or s["red"] > 0.00002),
]
allok = True
for ft, label, check in CHECKS:
    p = f"/tmp/tn2_{ft}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT, "-ss", str(ft),
                    "-frames:v", "1", p], check=True)
    im = np.asarray(Image.open(p).convert("RGB"), dtype=int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    s = {
        "bright": float((im.min(axis=2) > 200).mean()),
        "green": float(((g > 180) & (r < 120) & (g > b + 60)).mean()),
        "red": float(((r > 180) & (g < 140) & (b < 140)).mean()),
        "violet": float(((r > 120) & (b > 180) & (g < 140)).mean()),
    }
    ok = check(s)
    allok &= ok
    print(f"t={ft} {'PASS' if ok else 'FAIL'} [{label}] bright={s['bright']:.4f} "
          f"green={s['green']:.4f} red={s['red']:.5f} violet={s['violet']:.5f}")
    os.remove(p)
print("size:", os.path.getsize(OUT) // 1024, "KB")
print("THREE NAMES VERIFIED" if allok else "STILL FAILING")
