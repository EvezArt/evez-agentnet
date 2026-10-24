"""Hypercut: boot-detect trim + act verification, then hold the trimmed
visual at hypercut_visual.mp4 for the narration mux."""
import subprocess, os
import numpy as np
from PIL import Image

S = "/root/evez-agentnet/forge_output/render_pipeline"
RAW = f"{S}/hypercut_raw3.mp4"
VIS = f"{S}/hypercut_visual.mp4"

os.makedirs("/tmp/hyperprobe", exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", RAW, "-vf", "fps=2,scale=96:54",
                "/tmp/hyperprobe/f%04d.png"], check=True)
fs = sorted(os.listdir("/tmp/hyperprobe"))
boot = None
for f in fs:
    im = np.asarray(Image.open(f"/tmp/hyperprobe/{f}").convert("L"), dtype=float)
    if float((im > 30).mean()) > 0.15:
        boot = int(f[1:-4]) / 2.0
        break
for f in fs:
    os.remove(f"/tmp/hyperprobe/{f}")
print("boot:", boot)
assert boot is not None
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, boot-0.5):.2f}", "-i", RAW,
                "-t", "41", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", VIS], check=True)

allok = True
for ft, label in [(3, "names slam"), (9, "law strobe"), (20, "torus+records"),
                 (30, "laser night"), (37, "end card")]:
    p = f"/tmp/hv_{ft}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", VIS, "-ss", str(ft),
                    "-frames:v", "1", p], check=True)
    im = np.asarray(Image.open(p).convert("RGB"), dtype=int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    green = float(((g > 180) & (r < 120) & (g > b + 60)).mean())
    red = float(((r > 180) & (g < 140) & (b < 140)).mean())
    violet = float(((r > 120) & (b > 180) & (g < 140)).mean())
    yellow = float(((r > 200) & (g > 200) & (b < 120)).mean())
    lit = float((im.mean(axis=2) > 60).mean())
    ok = (green + red + violet + yellow) > 0.001 and lit > 0.02
    allok &= ok
    print(f"t={ft} {'PASS' if ok else 'FAIL'} [{label}] green={green:.4f} red={red:.4f} "
          f"violet={violet:.4f} yellow={yellow:.4f} lit={lit:.3f}")
    os.remove(p)
print("HYPERCUT VISUAL VERIFIED" if allok else "HYPERCUT VISUAL FAILING")
