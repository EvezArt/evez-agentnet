#!/usr/bin/env python3
"""MICRO-CHUNK — the last two mis-speaking segments, one sentence at a time.
Short takes render clean ~always (comedy bank proof). Each micro: lottery,
stats gate; stitched with 300ms gaps; replaces heal_010 / heal_013."""
import os, sys, time, random, subprocess, re
os.environ.setdefault("OMP_NUM_THREADS", "4")
try:
    os.nice(-5)
except PermissionError:
    pass
sys.path.insert(0, "/root/evez-davinci")
import numpy as np
import torch
from TTS.api import TTS

S = "/root/evez-agentnet/forge_output/render_pipeline"
import spoken_seeded as sd
sys.path.insert(0, S)
from doc_render_v3 import speech_stats, trim_seams

MICROS = {
    10: [
        "A Ukrainian kid, twenty two years old, sat at a Shelton Street address.",
        "The same address appears on a United States sanctions record.",
        "Another shell dissolved fourteen days after a regulated British firm verified its owner.",
    ],
    13: [
        "An append only record, hash chained.",
        "Every log sealed. Every dossier sealed. Every demand sealed.",
        "Even every mistake, sealed.",
        "Tampering shows itself in one command.",
        "The spine holds nearly twelve thousand events, and it grows while you listen.",
    ],
}

def render_one(tts, text, seed, out):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    tts.tts_to_file(text=text, speaker_wav=sd.REFS, language="en",
                    file_path=out, split_sentences=False,
                    temperature=0.65, top_k=45, top_p=0.85,
                    repetition_penalty=1.1, length_penalty=1.0)

def main():
    print("loading XTTS", flush=True)
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", "0.30",
                    f"{S}/gap_short.wav"], check=True)
    for idx, sentences in MICROS.items():
        takes = []
        for k, sent in enumerate(sentences):
            expected = len(sent) / 13.5
            ok = False
            for attempt in range(8):
                seed = sd.SEED + attempt * 613 + idx * 9109 + k * 17
                raw = f"{S}/doc_v2/micro_{idx}_{k}_{attempt}.wav"
                render_one(tts, sent, seed, raw)
                dur, speech = speech_stats(raw)
                ratio = speech / dur if dur else 0
                ok = ratio >= 0.60 and dur <= max(1.8 * expected, expected + 2.5) and dur > 0.5
                print(f"micro {idx}/{k} att {attempt}: dur={dur:.1f} ratio={ratio:.2f} "
                      f"{'OK' if ok else 'reroll'}", flush=True)
                if ok:
                    takes.append(raw)
                    break
            if not ok:
                print(f"micro {idx}/{k}: NO CLEAN TAKE — keeping prior segment", flush=True)
                takes = []
                break
        if not takes:
            continue
        lst = f"{S}/micro_concat_{idx}.txt"
        with open(lst, "w") as f:
            for p in takes:
                f.write(f"file '{p}'\n")
                f.write(f"file '{S}/gap_short.wav'\n")
        joined = f"{S}/micro_join_{idx}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", joined], check=True)
        final = f"{S}/doc_v2/heal_{idx:03d}.wav"
        trim_seams(joined, final)
        d, sp = speech_stats(final)
        print(f"seg {idx} MICRO-CHUNKED: dur={d:.1f} speech={sp:.1f} ratio={sp/d:.2f}", flush=True)
    print("MICRO PASS DONE", flush=True)

if __name__ == "__main__":
    main()
