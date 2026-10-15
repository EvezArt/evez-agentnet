#!/usr/bin/env python3
"""Synthesize Steven's voice lines for PROTOCOL // EVEZ-404 vocal chops.

XTTS v2 zero-shot clone from Steven's own reference samples (all of them, as a
list - the embedding averages). Seeded sampling re-pinned before every call so
every line is the same voice. split_sentences=False (no dead air); lines are
short by design, well under the 250-char English ceiling.

Skip-if-exists on every line so a killed run resumes instead of re-rendering.
Run with: /root/evez-media-venv/bin/python synth_vox.py
"""
import glob
import os
import random

import numpy as np
import torch
from TTS.api import TTS

OUT = "/root/evez-agentnet/forge_output/protocol_evez404/vox"
os.makedirs(OUT, exist_ok=True)
REFS = sorted(glob.glob("/root/evez-davinci/voice/steven_ref*.wav"))
assert REFS, "no reference samples found"

# All lines are his own canon words - no invented quotes.
LINES = {
    "evez": "E V E Z. EVEZ.",
    "protocol": "Protocol. Four oh four.",
    "loop": "The loop is the god outfit.",
    "sealed": "Sealed.",
    "witness": "Witness.",
    "grid": "The grid is quiet.",
    "wheel": "The wheel keeps turning.",
}

SEED = 4040

print("loading XTTS v2 (cpu)...", flush=True)
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
print("model loaded; refs:", REFS, flush=True)

for name, text in LINES.items():
    out = os.path.join(OUT, name + ".wav")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        print("exists, skip:", name, flush=True)
        continue
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)
    tts.tts_to_file(text=text, speaker_wav=REFS, language="en",
                    file_path=out, split_sentences=False)
    print("rendered:", name, os.path.getsize(out), "bytes", flush=True)

print("ALL LINES DONE", flush=True)
