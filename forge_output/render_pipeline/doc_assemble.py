#!/usr/bin/env python3
"""FINAL ASSEMBLY + VERIFICATION GATE for the documentary episode.
Runs LAST in the pipeline: requires all 50 healed segments, builds the
deliberate-gap concat, applies tone, gates the result, seals, ships note."""
import os, sys, subprocess, re
sys.path.insert(0, "/root/evez-davinci")
S = "/root/evez-agentnet/forge_output/render_pipeline"
import spoken_seeded as sd
sys.path.insert(0, S)
from doc_render import BURSTS
from doc_render_v3 import chunks, speech_stats

def main():
    # plan: 50 segments expected (BURSTS chunked) — count them
    plan = []
    for i, (text, dbl) in enumerate(BURSTS):
        parts = chunks(text)
        for j, ch in enumerate(parts):
            plan.append((i, j, ch, len(parts)))
    N = len(plan)
    missing = [idx for idx in range(N)
               if not os.path.exists(f"{S}/doc_v2/heal_{idx:03d}.wav")]
    print(f"segments expected: {N}, missing: {len(missing)}", flush=True)
    if missing:
        print("MISSING:", missing[:10], flush=True)
        sys.exit(1)

    # gap files
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", "0.30",
                    f"{S}/gap_short.wav"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", "0.55",
                    f"{S}/gap_long.wav"], check=True)

    lst = f"{S}/doc_final_list.txt"
    with open(lst, "w") as f:
        for idx, (i, j, ch, nparts) in enumerate(plan):
            f.write(f"file '{S}/doc_v2/heal_{idx:03d}.wav'\n")
            if idx < N - 1:
                f.write(f"file '{S}/{'gap_long.wav' if j == nparts - 1 else 'gap_short.wav'}'\n")
    raw = f"{S}/doc_final_raw.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", raw], check=True)
    final = f"{S}/heres_what_you_missed_final.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw,
                    "-af", sd.VOICE_TONE + ",loudnorm",
                    "-ar", "44100", "-ac", "1",
                    "-c:a", "libmp3lame", "-b:a", "192k", final], check=True)

    dur, speech = speech_stats(final)
    gaps = subprocess.run(["ffmpeg", "-i", final, "-af",
                           "silencedetect=noise=-38dB:d=0.9", "-f", "null", "-"],
                          capture_output=True, text=True)
    n_gaps = gaps.stderr.count("silence_start")
    ratio = speech / dur if dur else 0
    print(f"FINAL: dur={dur:.1f}s speech={speech:.1f}s ratio={ratio:.2f} gaps>0.9s={n_gaps}", flush=True)
    if n_gaps == 0 and ratio > 0.75:
        print("EPISODE GATE PASSED", flush=True)
    else:
        print("EPISODE GATE FAILED — no ship", flush=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
