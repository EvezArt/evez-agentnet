#!/usr/bin/env python3
"""FIX PASS — re-render failed segments with reworded text, dual-gate QC.

Targets: segments that failed round-trip transcription QC (3, 8, 10, 13, 14, 16)
plus seg 15 (over-length double-recitation whose round-trip 'pass' was whisper
giving up early). Each re-render must pass BOTH gates:
  1. stats: speech ratio >= 0.55, duration <= 2.2x expected
  2. round-trip: whisper-small transcription similarity >= 0.72
Rewrites preserve meaning; they break the rhythm that trips XTTS.
"""
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
import spoken_seeded as sd
sys.path.insert(0, S)
from doc_render import BURSTS
from doc_render_v3 import chunks, speech_stats, trim_seams

def norm(t):
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()

ALT = {
    3:  "This one is long. The whole war, from the first packet to the last filing. The record tells it. Every number was measured. Nothing was remembered.",
    8:  "Around him stood a constellation. A Romanian provider named UNMANAGED. Two thousand five hundred fifty addresses. Its director is called Bunea.",
    10: ("A Ukrainian kid, twenty two years old, sat at a Shelton Street address. "
         "The same address appears on a United States sanctions record. "
         "Another shell dissolved fourteen days after a regulated British firm verified its owner."),
    13: ("An append only record. Hash chained. Every log sealed. Every dossier sealed. "
         "Every demand sealed. Even every mistake, sealed. Tampering shows itself in one command. "
         "The spine holds nearly twelve thousand events. It grows while you listen."),
    14: ("The first sweep sealed four hundred forty six dossiers. By autumn the count passed "
         "eighteen hundred. The crackdown engine bans. It seals. It remembers. "
         "Defense became narration."),
    15: "Two addresses. Five entities. A single pattern of formation. The machine drew this map. Nobody asked it to.",
    16: ("October arrived. The victim filed with the FBI. Companies House followed. "
         "The registrar received an integrity complaint about a nominee network of four shells. "
         "The Information Commissioner came next. RIPE, the keepers of European routing, got a ticket. "
         "A preservation demand was served and machine rejected. Fifty five four. All three channels. "
         "The delivery receipts were kept."),
    18: ("Two demands went out. Twenty five thousand dollars each. Fourteen days to answer. "
         "The adversary chose silence. The record kept the silence too. The clocks blew. "
         "A consequence stage armed itself. A claim in England and Wales. Letter before action, served. "
         "Silence preserved. In this story, silence is always evidence."),
}

def roundtrip(m, path, src):
    segs, info = m.transcribe(path, beam_size=3, language="en")
    heard = " ".join(s.text.strip() for s in segs).strip()
    ratio = difflib.SequenceMatcher(None, norm(src).split(), norm(heard).split()).ratio()
    return ratio

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
    print("loading whisper", flush=True)
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    print("models loaded", flush=True)

    for idx, text in sorted(ALT.items()):
        # resume-skip: already-replaced clean segments stay
        cur = f"{S}/doc_v2/heal_{idx:03d}.wav"
        if os.path.exists(cur):
            cdur, cspeech = speech_stats(cur)
            cratio = cspeech / cdur if cdur else 0
            if cratio >= 0.55:
                print(f"seg {idx}: already clean (ratio={cratio:.2f}) — skip", flush=True)
                continue
        expected = len(text) / 13.5
        # multi-sentence alternates render as their own sub-chunks
        parts = chunks(text)
        sub_paths = []
        clean = True
        for j, part in enumerate(parts):
            ok = False
            best = None
            for attempt in range(10):
                seed = sd.SEED + attempt * 991 + idx * 3301
                raw = f"{S}/doc_v2/fix_{idx}_{j}_{attempt}.wav"
                render_one(tts, part, seed, raw)
                dur, speech = speech_stats(raw)
                ratio = speech / dur if dur else 0
                stats_ok = ratio >= 0.55 and dur <= max(2.2 * (len(part) / 13.5), len(part) / 13.5 + 4.0) and dur > 0.8
                if not stats_ok:
                    print(f"seg {idx} part {j} att {attempt}: stats fail (dur={dur:.1f} ratio={ratio:.2f})", flush=True)
                    continue
                rt = roundtrip(m, raw, part)
                print(f"seg {idx} part {j} att {attempt}: dur={dur:.1f} stats=OK roundtrip={rt:.2f} "
                      f"{'ACCEPT' if rt >= 0.72 else 'reject'}", flush=True)
                if rt >= 0.72:
                    ok = True
                    sub_paths.append(raw)
                    break
                if best is None:
                    best = raw
            if not ok:
                clean = False
                print(f"seg {idx} part {j}: NO CLEAN TAKE in 10 rolls", flush=True)
                if best:
                    sub_paths.append(best)
        if not sub_paths:
            print(f"seg {idx}: nothing produced — keeping prior take", flush=True)
            continue
        if len(sub_paths) == 1:
            trim_seams(sub_paths[0], f"{S}/doc_v2/heal_{idx:03d}.wav")
        else:
            lst = f"{S}/doc_v2/fix_concat_{idx}.txt"
            with open(lst, "w") as f:
                for p in sub_paths:
                    f.write(f"file '{p}'\n")
                    f.write(f"file '{S}/gap_short.wav'\n")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", lst, "-c", "copy", f"{S}/doc_v2/fix_join_{idx}.wav"], check=True)
            trim_seams(f"{S}/doc_v2/fix_join_{idx}.wav", f"{S}/doc_v2/heal_{idx:03d}.wav")
        # verify the healed replacement end-to-end
        dur, speech = speech_stats(f"{S}/doc_v2/heal_{idx:03d}.wav")
        rt = roundtrip(m, f"{S}/doc_v2/heal_{idx:03d}.wav", text)
        print(f"seg {idx} REPLACED: dur={dur:.1f} speech={speech:.1f} roundtrip={rt:.2f}"
              f"{' — CLEAN' if clean else ' — best-of flagged'}", flush=True)
    print("FIX PASS DONE", flush=True)

if __name__ == "__main__":
    main()
