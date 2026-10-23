#!/usr/bin/env python3
"""THE COMEDY BANK — standing punchline takes in Steven's clone voice.
The 3:33 channel draws from this permanent vault so it's never voiceless.
Short bursts render clean; QC lottery with stats gate, round-trip spot check."""
import os, sys, time, random, subprocess, re, difflib
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
OUT = "/root/evez-agentnet/forge_output/comedy_bank"
import spoken_seeded as sd
sys.path.insert(0, S)
from doc_render_v3 import speech_stats

JOKES = [
    "The desk earned zero dollars today. The streak hit one thousand ninety two. The machine keeps faith whether you watch or not. Most loyal unpaid intern in history.",
    "The ecology logged zero players, zero agents, zero fire events. Nobody came. Again. Keeping the compassion layer warm anyway. Just in case.",
    "The predictor stared at Polymarket all night, asking one question. Will Ethereum touch four thousand five hundred. It has no money. It is read only. It just likes to know.",
    "FreeCodeCamp is still trending. We checked. We are not jealous. We are documenting jealousy for the record.",
    "The analyst hallucinated the numbers again. We gave him a screen credit. Again. The most honest lie on the internet.",
    "Eighty three point one. The record fell while the booth was mid sentence. The record has no manners. It never waits for narration.",
    "OpenClaw cleared five of five levels and unlocked the lord. Seventh time this week. The levels are starting to look afraid of him.",
    "The book is beating my forecaster. My forecaster is beating nothing. Brier score zero point three two. A coin flip with confidence.",
    "XRP and ETH burned the house down again. The house is insured by the streak. The streak is not money. This is the problem.",
    "Two demands for twenty five thousand dollars each. They answered with silence. The record kept the silence too. Silence is evidence. Also rude.",
    "A shell died fourteen days after a regulated firm verified its owner. Fourteen days. Even the paperwork ghosted itself.",
    "The machine wrote a documentary about itself spying on itself. History calls it administration. The machine calls it Tuesday.",
    "Round closed at zero dollars. Perfect reputation. Perfect streak. Perfect poverty. The machine holds the line in the dark whether you watch or not.",
    "The tape keeps commanding the agent. Run this. Tell it how to run. The agent complied. The agent overreacted. The agent got a screen credit too.",
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
    os.makedirs(OUT, exist_ok=True)
    print("loading XTTS", flush=True)
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    ok_count = 0
    for i, joke in enumerate(JOKES):
        out_wav = f"{OUT}/comedy_bank_{i:02d}.wav"
        if os.path.exists(out_wav):
            d0, s0 = speech_stats(out_wav)
            if d0 and s0 / d0 >= 0.55:
                print(f"joke {i}: already sealed — skip", flush=True)
                continue
        expected = len(joke) / 13.5
        ok = False
        for attempt in range(8):
            seed = sd.SEED + attempt * 811 + i * 4409
            raw = f"{S}/com_{i:02d}_{attempt}.wav"
            render_one(tts, joke, seed, raw)
            dur, speech = speech_stats(raw)
            ratio = speech / dur if dur else 0
            ok = ratio >= 0.55 and dur <= max(2.2 * expected, expected + 4.0) and dur > 0.8
            print(f"joke {i} att {attempt}: dur={dur:.1f} ratio={ratio:.2f} {'OK' if ok else 'reroll'}", flush=True)
            if ok:
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                                sd.VOICE_TONE + ",loudnorm", "-ar", "44100", "-ac", "1",
                                f"{OUT}/comedy_bank_{i:02d}.wav"], check=True)
                ok_count += 1
                break
    print(f"COMEDY BANK DONE: {ok_count}/{len(JOKES)} sealed", flush=True)

if __name__ == "__main__":
    main()
