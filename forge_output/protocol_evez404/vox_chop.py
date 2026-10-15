#!/usr/bin/env python3
"""Chop Steven's cloned voice into PROTOCOL // EVEZ-404.

Takes the XTTS-rendered lines in vox/ and cuts them into the track:
- full-line drops ("E V E Z" at the slam-back, canon lines in the breakdown)
- 16th-note stutter rolls of grains in wave 2, alternating L/R pans
- +5-semitone nightcore doubles (resampled grains) for the doppleganger ghosts
All placements are on the 204 BPM grid of the existing render.

Run with system python3 (numpy only): python3 vox_chop.py
"""
import glob
import os
import wave

import numpy as np

SR = 44100
BPM = 204
BAR = 60.0 / BPM * 4
SIXTEENTH = BAR / 16
BASE = "/root/evez-agentnet/forge_output/protocol_evez404"


def load_wav_mono(path, target_sr=SR):
    with wave.open(path) as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch)
        mono = raw.mean(axis=1).astype(np.float64) / 32767
    if sr != target_sr:
        mono = np.interp(np.arange(0, len(mono), sr / target_sr), np.arange(len(mono)), mono)
    return trim_silence(mono)


def trim_silence(x, thresh=0.015, pad_ms=30):
    env = np.abs(x)
    mask = env > thresh * (np.max(env) or 1.0)
    if not mask.any():
        return x
    i0 = int(np.argmax(mask))
    i1 = len(x) - int(np.argmax(mask[::-1]))
    pad = int(SR * pad_ms / 1000)
    return x[max(0, i0 - pad): min(len(x), i1 + pad)]


def envelope(x, edge_ms=8):
    e = int(SR * edge_ms / 1000)
    if len(x) <= 2 * e:
        return x
    ramp = np.hanning(2 * e)[:e]
    x[:e] *= ramp
    x[-e:] *= ramp[::-1]
    return x


def grain(src, start_s, dur_ms=120):
    i = int(start_s * SR)
    j = min(len(src), i + int(SR * dur_ms / 1000))
    if j - i < int(SR * 0.03):
        # not enough left at this offset; wrap around
        i = i % max(1, len(src) - int(SR * dur_ms / 1000))
        j = i + int(SR * dur_ms / 1000)
    return envelope(src[i:j].copy())


def pitch_up_5st(x):
    """+5 semitones: play faster (shorter, higher) - the nightcore double."""
    factor = 2 ** (5 / 12)
    return np.interp(np.arange(0, len(x), factor), np.arange(len(x)), x)


class VoxMix:
    def __init__(self, n):
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def add(self, sig, at, pan, gain=1.0):
        i = int(at * SR)
        j = min(len(self.L), i + len(sig))
        if j <= i:
            return
        s = sig[: j - i] * gain
        l = np.sqrt(max(0.0, (1 - pan) / 2 + 0.5))
        r = np.sqrt(max(0.0, (pan + 1) / 2 + 0.5))
        self.L[i:j] += s * min(1.0, l * 1.41)
        self.R[i:j] += s * min(1.0, r * 1.41)


def main():
    # base track
    with wave.open(os.path.join(BASE, "protocol_evez404.wav")) as w:
        n = w.getnframes()
        base = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, 2).astype(np.float64) / 32767

    lines = {}
    for p in sorted(glob.glob(os.path.join(BASE, "vox", "*.wav"))):
        lines[os.path.splitext(os.path.basename(p))[0]] = load_wav_mono(p)
    need = ["evez", "protocol", "loop", "sealed", "witness", "grid", "wheel"]
    missing = [k for k in need if k not in lines]
    assert not missing, "missing voice lines: %s" % missing

    V = VoxMix(n)
    placements = []

    # ---- slam-back after the time-dilation drop: the name, center, loud ----
    slam = 14.12 + BAR
    V.add(envelope(lines["evez"].copy()), slam, 0.0, 0.95)
    placements.append(("evez-full", slam))

    # ---- breakdown (bars 26-30): canon lines, wide and quiet ----
    V.add(envelope(lines["loop"].copy()), 26 * BAR, -0.35, 0.55)
    V.add(envelope(lines["grid"].copy()), 28 * BAR, 0.35, 0.5)
    placements += [("loop", 26 * BAR), ("grid", 28 * BAR)]

    # ---- wave 1 (bars 18-25): single witness/sealed grains on necklace hits ----
    seed = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0]
    for bar in range(18, 26):
        for s16 in range(16):
            if seed[s16] and s16 in (0, 8):
                src = lines["witness"] if s16 else lines["sealed"]
                g = grain(src, 0.02, 110)
                V.add(g, bar * BAR + s16 * SIXTEENTH, -0.6 if s16 else 0.6, 0.6)
                placements.append(("grain-w1", bar * BAR + s16 * SIXTEENTH))

    # ---- wave 2 (bars 31-43): stutter rolls + nightcore +5st doubles ----
    for bar in range(31, 44, 2):
        t0 = bar * BAR
        # pick a fresh offset into "protocol" for variety
        off = ((bar * 37) % 40) / 100.0
        g0 = grain(lines["protocol"], off, 130)
        g_night = pitch_up_5st(g0)
        pan = -0.65 if bar % 4 else 0.65
        for k in range(4):  # 16th-note stutter roll
            at = t0 + k * SIXTEENTH * 2
            V.add(g0, at, pan, 0.62)
            V.add(g_night, at + SIXTEENTH, -pan, 0.45)  # doppleganger answers
            placements.append(("stutter", at))
        # one clear "evez" grain per 4th bar
        if bar % 4 == 2:
            V.add(grain(lines["evez"], 0.05, 150), t0 + BAR / 2, 0.0, 0.8)
            placements.append(("evez-grain", t0 + BAR / 2))

    # ---- outro (bar 42+): the wheel line, fading under ----
    V.add(envelope(lines["wheel"].copy()), 42 * BAR, 0.2, 0.45)
    placements.append(("wheel", 42 * BAR))

    # ---- mix, soft-clip, normalize to match the base master ----
    L = base[:, 0] + V.L * 0.9
    R = base[:, 1] + V.R * 0.9
    L, R = np.tanh(L * 1.25), np.tanh(R * 1.25)
    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) or 1.0
    L, R = L / peak * 0.85, R / peak * 0.85
    stereo = np.stack([L, R], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    out = os.path.join(BASE, "PROTOCOL_EVEZ_404_VOX.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    vox_energy = 20 * np.log10(np.sqrt(np.mean((V.L + V.R) ** 2)) + 1e-12)
    print("VOX MIX:", out)
    print("placements:", len(placements), "| vox bus energy %.1f dB | duration %.2fs" % (vox_energy, n / SR))
    for name, at in placements[:12]:
        print("  %-12s @ %.2fs" % (name, at))
    print("  ... (%d total)" % len(placements))


if __name__ == "__main__":
    main()
