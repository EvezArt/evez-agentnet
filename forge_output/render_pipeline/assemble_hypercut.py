#!/usr/bin/env python3
"""HYPERCUT FINAL — place the 9 voice lines against the 40s visual, drone bed,
mux, verify, seal, ship."""
import subprocess, os, re, sys

S = "/root/evez-agentnet/forge_output/render_pipeline"
VIS = f"{S}/hypercut_visual.mp4"
OUT = "/root/evez-agentnet/forge_output/films/the_three_names_hypercut.mp4"

def dur(p):
    d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", p],
                       capture_output=True, text=True).stdout
    return float(re.search(r"duration=([\d.]+)", d).group(1))

# (file, start_at_seconds)
TIMES = [
    ("hyp_n0", 0.6), ("hyp_n1", 2.6), ("hyp_n2", 4.8), ("hyp_n3", 7.2),
    ("hyp_n4", 13.6), ("hyp_n5", 15.2), ("hyp_n6", 20.8),
    ("hyp_n7", 32.5), ("hyp_n8", 35.8),
]
missing = [t for t, _ in TIMES if not os.path.exists(f"{S}/{t}.wav")]
if missing:
    print("MISSING VOICES:", missing)
    sys.exit(1)

parts = []
for i, (tag, at) in enumerate(TIMES):
    parts.append(
        f"[{i+1}:a]adelay={int(at*1000)}|{int(at*1000)},apad[a{i}]")
fc = ";".join(parts) + ";" + \
     f"aevalsrc=sin(2*PI*55*t)+0.4*sin(2*PI*110*t):d=42,volume=0.05[dr];" + \
     "[" + "][".join(f"a{i}" for i in range(len(TIMES))) + "][dr]" + \
     f"amix=inputs={len(TIMES)+1}:duration=first:normalize=0," \
     f"atrim=0:40,loudnorm,afade=t=out:st=38:d=2[a]"

cmd = ["ffmpeg", "-y", "-v", "error", "-i", VIS]
for tag, _ in TIMES:
    cmd += ["-i", f"{S}/{tag}.wav"]
cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", OUT]
subprocess.run(cmd, check=True)
d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", OUT],
                   capture_output=True, text=True).stdout
print("HYPERCUT FILM:", [l for l in d.splitlines() if l.startswith("duration")][0])
print("size:", os.path.getsize(OUT) // 1024, "KB")

sys.path.insert(0, "/root/.openclaw/workspace/skills/evez-crackdown/scripts")
import crackdown
sha = subprocess.run(["sha256sum", OUT], capture_output=True, text=True).stdout[:32]
h = crackdown.seal("the_three_names_hypercut", {
    "artifact": "forge_output/films/the_three_names_hypercut.mp4", "sha256": sha,
    "duration_s": 40.0,
    "form": "40s hypercut: three pitch-forged voices (deep 0.55 / natural / high 1.3) trading lines over the feral visual, drone bed",
    "note": "one throat, three witnesses: the deep voice names the law, the natural voice carries the hand, the high voice shouts the record; sealed as the fast canon"})
print("hypercut seal ->", h[:16])
