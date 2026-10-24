"""Boot-detect + trim + verify: find the first lit frame (chrome up), trim to it,
verify all five acts at film-relative times."""
import subprocess, os
import numpy as np
from PIL import Image

RAW = "/root/evez-agentnet/forge_output/render_pipeline/feral_take2_raw.mp4"
OUT = "/root/evez-agentnet/forge_output/films/the_three_names_feral.mp4"

# 1) sample 2fps downscale series to find boot
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", RAW,
                "-vf", "fps=2,scale=96:54", "/tmp/feralprobe/f%04d.png"], check=True)
os.makedirs("/tmp/feralprobe", exist_ok=True)
boot = None
fs = sorted(os.listdir("/tmp/feralprobe"))
for f in fs:
    im = np.asarray(Image.open(f"/tmp/feralprobe/{f}").convert("L"), dtype=float)
    if float((im > 30).mean()) > 0.15:
        boot = int(f[1:-4]) / 2.0
        break
for f in fs:
    os.remove(f"/tmp/feralprobe/{f}")
print("boot (first lit frame):", boot)
assert boot is not None, "no lit frame in 175s — chrome never came up"
lead = max(0.0, boot - 1.0)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{lead:.2f}", "-i", RAW,
                "-t", "96", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], check=True)
d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", OUT],
                   capture_output=True, text=True).stdout
print("duration:", [l for l in d.splitlines() if l.startswith("duration")][0])

# 2) five-act verification
allok = True
for ft, label in [(8, "creature+names"), (28, "law strobe"), (50, "torus rite"),
                 (70, "laser eyes"), (90, "end card")]:
    p = f"/tmp/fv2_{ft}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT, "-ss", str(ft),
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
print("size:", os.path.getsize(OUT) // 1024, "KB")
print("FERAL VERIFIED — BOOT-TRIMMED" if allok else "FERAL STILL FAILING")
