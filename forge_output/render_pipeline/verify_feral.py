import subprocess, os
import numpy as np
from PIL import Image
OUT = "/root/evez-agentnet/forge_output/films/the_three_names_feral.mp4"
d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", OUT], capture_output=True, text=True).stdout
print("duration:", [l for l in d.splitlines() if l.startswith("duration")][0])
allok = True
for ft, label in [(8, "creature+names"), (28, "the law strobe"), (50, "torus rite"),
                  (70, "laser eyes night"), (90, "end card")]:
    p = f"/tmp/fv_{ft}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", OUT, "-ss", str(ft), "-frames:v", "1", p], check=True)
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
print("FERAL VERIFIED" if allok else "FERAL FAILING")
