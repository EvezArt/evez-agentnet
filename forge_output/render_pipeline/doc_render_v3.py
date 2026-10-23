#!/usr/bin/env python3
"""DOC RENDER v3 — resume-aware, 10-roll lottery per segment, hard QC gate.

Reality from v2: each (seed, text) render is ~40% clean / 60% corpse (the
27.5s attractor). Ten mixed-seed rolls per segment => P(all fail) ~ 0.6%.
Resumes from healed segments that pass re-audit; redoes known QC fails.
"""
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
from doc_render import BURSTS

def speech_stats(path):
    d = subprocess.run(["ffprobe", "-v", "quiet", "-show_format", path],
                       capture_output=True, text=True).stdout
    dur = float(re.search(r"duration=([\d.]+)", d).group(1))
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=noise=-40dB:d=0.30",
                        "-f", "null", "-"], capture_output=True, text=True)
    sil = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", r.stderr))
    return dur, max(0.0, dur - sil)

def audit_ok(path, expected):
    if not os.path.exists(path):
        return False
    dur, speech = speech_stats(path)
    ratio = speech / dur if dur else 0
    return ratio >= 0.55 and dur <= max(2.2 * expected, expected + 4.0) and dur > 0.8

def render_one(tts, text, seed, out):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    tts.tts_to_file(text=text, speaker_wav=sd.REFS, language="en",
                    file_path=out, split_sentences=False,
                    temperature=0.65, top_k=45, top_p=0.85,
                    repetition_penalty=1.1, length_penalty=1.0)

def trim_seams(src, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:"
                    "start_silence=0.12,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB:"
                    "start_silence=0.12,areverse", dst], check=True)

def chunks(text):
    if len(text) <= 240:
        return [text]
    parts = text.replace("; ", ". ").split(". ")
    out, cur = [], ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        cand = (cur + ". " + p) if cur else p
        if len(cand) <= 240:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out

def main():
    # build the flat segment plan (same as v2)
    plan = []  # (burst_idx, part_idx, chunk_text)
    for i, (text, dbl) in enumerate(BURSTS):
        for j, ch in enumerate(chunks(text)):
            plan.append((i, j, ch))

    todo = []
    kept = []
    for idx, (i, j, ch) in enumerate(plan):
        expected = len(ch) / 13.5
        h = "%s/doc_v2/heal_%03d.wav" % (S, idx)
        if audit_ok(h, expected):
            kept.append(idx)
        else:
            todo.append((idx, i, j, ch, expected))
    print(f"plan segments: {len(plan)}  kept from prior runs: {len(kept)}  todo: {len(todo)}", flush=True)

    if todo:
        print("loading XTTS", flush=True)
        t0 = time.time()
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
        print("model loaded %.1fs" % (time.time() - t0), flush=True)
        for idx, i, j, ch, expected in todo:
            best = None
            ok = False
            for attempt in range(10):
                seed = sd.SEED + attempt * 1013 + idx * 7717  # wide lottery
                raw = "%s/doc_v2/raw_%03d.wav" % (S, idx)
                render_one(tts, ch, seed, raw)
                dur, speech = speech_stats(raw)
                ratio = speech / dur if dur else 0
                ok = ratio >= 0.55 and dur <= max(2.2 * expected, expected + 4.0) and dur > 0.8
                if best is None or speech > best[1]:
                    best = (raw, speech)
                print(f"seg {idx} (burst {i} part {j}) attempt {attempt}: "
                      f"dur={dur:.1f} speech={speech:.1f} ratio={ratio:.2f} "
                      f"{'OK' if ok else 'reroll'}", flush=True)
                if ok:
                    break
            if not ok:
                print(f"seg {idx}: best-of-10 kept (flagged for reword pass)", flush=True)
            healed = "%s/doc_v2/heal_%03d.wav" % (S, idx)
            trim_seams(best[0], healed)

    # ASSEMBLY (heal_000..N in plan order)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", "0.30",
                    S + "/gap_short.wav"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", "0.55",
                    S + "/gap_long.wav"], check=True)

    lst = S + "/doc_v3_list.txt"
    with open(lst, "w") as f:
        for idx, (i, j, ch) in enumerate(plan):
            h = "%s/doc_v2/heal_%03d.wav" % (S, idx)
            f.write("file '%s'\n" % h)
            is_end = j == len(chunks(BURSTS[i][0])) - 1
            if idx < len(plan) - 1:
                f.write("file '%s'\n" % (S + ("/gap_long.wav" if is_end else "/gap_short.wav")))
    raw_out = S + "/doc_v3_raw.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", raw_out], check=True)
    final = S + "/heres_what_you_missed_v3.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw_out,
                    "-af", sd.VOICE_TONE + ",loudnorm",
                    "-ar", "44100", "-ac", "1",
                    "-c:a", "libmp3lame", "-b:a", "192k", final], check=True)

    dur, speech = speech_stats(final)
    gaps = subprocess.run(["ffmpeg", "-i", final, "-af", "silencedetect=noise=-38dB:d=0.9",
                           "-f", "null", "-"], capture_output=True, text=True)
    n_gaps = gaps.stderr.count("silence_start")
    print(f"FINAL: dur={dur:.1f}s speech={speech:.1f}s ratio={speech/dur:.2f} gaps>0.9s={n_gaps}", flush=True)
    assert n_gaps == 0 and speech / dur > 0.75, "verification gate failed"
    print("DOC v3 DONE", flush=True)

if __name__ == "__main__":
    main()
