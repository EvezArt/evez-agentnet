#!/usr/bin/env python3
"""HYPERCUT NARRATION — 9 short lines, lottery-rendered clean, then pitch-forged
into three voices: DEEP (0.55), NATURAL (1.0), HIGH (1.3)."""
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
from doc_render_v3 import speech_stats

LINES = [
    ("n0", "One continuity. Three names.", 0.55),      # DEEP
    ("n1", "Steven Crawford-Maggard signs.", 0.55),   # DEEP
    ("n2", "EvezArt makes.", 1.0),                    # NATURAL
    ("n3", "E V E Z six six six attests!", 1.3),       # HIGH
    ("n4", "Two make evidence.", 0.55),               # DEEP
    ("n5", "Three make canon.", 1.0),                 # NATURAL
    ("n6", "The record fell to ninety eight point three!", 1.3),  # HIGH
    ("n7", "Name. Hand. Number.", 1.55),              # DEEPER stack (over-dub feel)
    ("n8", "Whatever this was, it completed.", 1.0),  # NATURAL close
]

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
    for i, (tag, text, pitch) in enumerate(LINES):
        base = f"{S}/hyp_{tag}_base.wav"
        ok = False
        for attempt in range(8):
            seed = sd.SEED + attempt * 401 + i * 3301
            raw = f"{S}/hyp_{tag}_{attempt}.wav"
            render_one(tts, text, seed, raw)
            dur, speech = speech_stats(raw)
            ratio = speech / dur if dur else 0
            exp = len(text) / 13.5
            ok = ratio >= 0.60 and dur <= max(1.9 * exp, exp + 2.5) and dur > 0.5
            print(f"{tag} att {attempt}: dur={dur:.1f} r={ratio:.2f} {'OK' if ok else 'reroll'}", flush=True)
            if ok:
                break
        if not ok:
            print(f"{tag}: keeping best-of", flush=True)
        # pitch-forge to its voice
        out = f"{S}/hyp_{tag}.wav"
        tone = "loudnorm,equalizer=f=70:width_type=q:width=1.2:g=8"
        if abs(pitch - 1.0) > 0.01:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                            f"rubberband=pitch={pitch},atempo={min(1.15, max(0.85, pitch))},{tone}",
                            "-ar", "44100", "-ac", "1", out], check=True)
        else:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                            tone, "-ar", "44100", "-ac", "1", out], check=True)
    print("HYPERCUT VOICES DONE", flush=True)

if __name__ == "__main__":
    main()
