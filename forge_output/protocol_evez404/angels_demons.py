#!/usr/bin/env python3
"""ANGELS & DEMONS — the Steven/EVEZ binary, rendered.

The theological binary from Steven's spec: consonant supersaw angel stacks vs
distorted industrial demon shadow — and BOTH voices are his own cloned voice:
granular 8x-stretched into the ethereal choir halo (angel), pitched-down and
bitcrushed (demon). Tempo illusion: half-time 98 feel collapsing into 392-BPM
micro-slice snare bursts, with a Life-Flash vacuum at bar 20.

Sections (174 BPM, bar=1.379s, 44 bars ~ 60.7s):
  0-3   THE HALO        granular voice-choir + binaural theta bed + KS harp
  4-11  DEMONS RISING   reese bass + half-time kick + metal hits
  12-19 TEMPO COLLAPSE  full breakcore, 16th hats, 64th snare micro-rolls
  20    LIFE FLASH      one-bar vacuum: nightcore vox tail + held choir
  21-31 THE UNION       angel supersaw theme vs bitcrushed demon answer
  32-39 THE ASCENT      riser + accelerating rolls
  40-43  RESOLUTION     the halo returns alone

Run: python3 angels_demons.py [out.wav]   (system python3, numpy only)
"""
import argparse
import glob
import os
import wave

import numpy as np

SR = 44100
BPM = 174
BAR = 60.0 / BPM * 4
BASE_D3 = 146.832
HIJAZ = [1.0, 16/15, 5/4, 4/3, 3/2, 8/5, 15/8, 2.0]
CRAB = [0, 2, 1, 4, 5, 4, 2, 7]
VOXDIR = "/root/evez-agentnet/forge_output/protocol_evez404/vox"


def load_wav_mono(path, target_sr=SR):
    with wave.open(path) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch)
        mono = raw.mean(axis=1).astype(np.float64) / 32767
    if sr != target_sr:
        mono = np.interp(np.arange(0, len(mono), sr / target_sr), np.arange(len(mono)), mono)
    return mono


def fft_bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def envelope(x, edge_ms=8):
    e = int(SR * edge_ms / 1000)
    if len(x) <= 2 * e:
        return x
    ramp = np.hanning(2 * e)[:e]
    y = x.copy()
    y[:e] *= ramp
    y[-e:] *= ramp[::-1]
    return y


def granular_stretch(x, stretch=8.0, grain_ms=50, overlap=0.75):
    """8x-stretched voice -> the angel-choir halo (his Bus 2 spec)."""
    gs = int(SR * grain_ms / 1000)
    hop = max(1, int(gs * (1 - overlap)))
    out_len = int(len(x) * stretch)
    out = np.zeros(out_len + gs)
    win = np.hanning(gs)
    ngrains = out_len // hop
    for i in range(ngrains):
        src_pos = int(i * hop / stretch)
        if src_pos + gs > len(x):
            src_pos = max(0, len(x) - gs)
        g = x[src_pos:src_pos + gs] * win
        out[i * hop: i * hop + gs] += g
    out = out[:out_len]
    m = np.max(np.abs(out)) or 1.0
    return out / m


def pitch_shift(x, factor):
    """factor>1 = higher & shorter (resample)."""
    return np.interp(np.arange(0, len(x), factor), np.arange(len(x)), x)


def ks_note(freq, dur, damp=0.952, seed=None):
    rng = np.random.default_rng(seed)
    n = max(8, int(SR / freq))
    buf = rng.uniform(-1, 1, n)
    out = np.zeros(int(SR * dur))
    idx = 0
    for i in range(len(out)):
        nxt = (idx + 1) % n
        buf[idx] = 0.5 * (buf[idx] + buf[nxt]) * damp
        out[i] = buf[idx]
        idx = nxt
    return out * np.exp(-np.linspace(0, 4.5, len(out)))


def bandpass_noise(dur, lo, hi, seed=None):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, int(SR * dur))
    return fft_bandpass(x, lo, hi)


def kick(seed=None):
    t = np.arange(int(SR * 0.14)) / SR
    sweep = 155 * (36.71 / 155) ** (t / 0.09)
    return np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t / 0.045) * 0.9


def snare(dur=0.065, lo=1200, hi=3200, seed=None):
    n = bandpass_noise(dur, lo, hi, seed)
    t = np.arange(len(n)) / SR
    return n * np.exp(-t / (dur * 0.35))


def metal_hit(seed=None):
    """Demon percussion: noise ring-modulated at 2.7 kHz — industrial clank."""
    n = bandpass_noise(0.12, 300, 4000, seed)
    t = np.arange(len(n)) / SR
    return n * np.sin(2 * np.pi * 2700 * t) * np.exp(-t / 0.03) * 0.8


def reese(freq, dur):
    """Bus 1: detuned saw pair + comb + slow LFO — the reese bass."""
    t = np.arange(int(SR * dur)) / SR
    s1 = 2 * ((freq * 1.012 * t) % 1.0) - 1
    s2 = 2 * ((freq * 0.988 * t) % 1.0) - 1
    sig = s1 + s2
    lfo = 1 + 0.22 * np.sin(2 * np.pi * 0.4 * t)
    comb = sig + np.roll(sig, int(SR * 0.011))
    return fft_bandpass((sig * lfo * 0.6 + comb * 0.25), 20, 480)


def supersaw(freq, dur, voices=7):
    """The angel stack: 7 detuned saws, slow-attack."""
    t = np.arange(int(SR * dur)) / SR
    out = np.zeros(len(t))
    for k in range(voices):
        det = (k - voices // 2) * 0.004
        out += 2 * ((freq * (1 + det) * t) % 1.0) - 1
    out /= voices
    env = np.minimum(1.0, np.linspace(0, 0.25, len(t))) * np.minimum(1.0, np.linspace(dur, dur - 0.6, len(t)) + 1.0)
    return out * env


def riser(dur):
    n = bandpass_noise(dur, 3500, 12000, seed=77)
    t = np.linspace(0, 1, len(n)) ** 2
    return n * t


class Mix:
    def __init__(self, n):
        self.L = np.zeros(n)
        self.R = np.zeros(n)

    def add(self, sig, at, pan, gain=1.0):
        i = int(at * SR)
        j = min(self.L.size, i + len(sig))
        if j <= i:
            return
        s = sig[: j - i] * gain
        l = np.sqrt(max(0.0, (1 - pan) / 2 + 0.5))
        r = np.sqrt(max(0.0, (pan + 1) / 2 + 0.5))
        self.L[i:j] += s * min(1.0, l * 1.41)
        self.R[i:j] += s * min(1.0, r * 1.41)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="angels_and_demons.wav")
    a = ap.parse_args()
    bars = 44
    M = Mix(int(SR * (BAR * bars + 4)))

    # ---- his voice, both robes ----
    lines = {os.path.splitext(os.path.basename(p))[0]: load_wav_mono(p)
             for p in glob.glob(os.path.join(VOXDIR, "*.wav"))}
    assert {"loop", "wheel", "evez", "sealed", "witness"} <= set(lines), "vox lines missing"

    halo_src = np.concatenate([lines["loop"], np.zeros(SR // 2), lines["wheel"]])
    halo = granular_stretch(halo_src, stretch=8.0)
    halo = fft_bandpass(halo, 250, 3400)          # the voice band = the choir
    halo_chorus = halo + np.roll(halo, int(SR * 0.021)) * 0.5
    halo_len = int(BAR * 16 * SR)
    halo = np.resize(envelope(halo_chorus[:halo_len] / (np.max(np.abs(halo_chorus)) or 1.0)), halo_len)

    demon = {}
    for k in ("sealed", "witness"):
        d = pitch_shift(lines[k], 0.55)           # ~10 semitones down
        d = np.round(d * 8) / 8                    # bitcrush
        t = np.arange(len(d)) / SR
        d = d * np.sin(2 * np.pi * 66.6 * t) * 2.2  # ring-mod shadow
        demon[k] = envelope(d)

    # ---- Bus 1: binaural theta bed (the EVEZ signature) ----
    dur_total = BAR * bars
    t = np.arange(int(SR * dur_total)) / SR
    fade = np.minimum(1.0, np.linspace(0, 8, len(t))) * np.minimum(1.0, np.linspace(dur_total, dur_total - 6, len(t)) + 1.0)
    M.L[:len(t)] += (np.sin(2 * np.pi * 36.71 * t) * 0.14 + np.sin(2 * np.pi * 73.42 * t) * 0.05) * fade
    M.R[:len(t)] += (np.sin(2 * np.pi * 42.71 * t) * 0.14 + np.sin(2 * np.pi * 79.42 * t) * 0.05) * fade

    seed16 = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0]
    sixteenth = BAR / 16

    for bar in range(bars):
        t0 = bar * BAR
        # ---- THE HALO (0-3) and RESOLUTION (40-43): choir + KS harp ----
        if bar < 4 or bar >= 40:
            M.add(halo, t0, -0.15, 0.55 if bar < 4 else 0.5)
            for i, deg in enumerate([0, 4, 2, 5]):  # D A F# Bb harp
                M.add(ks_note(BASE_D3 * HIJAZ[deg] * 2, 0.9, 0.96), t0 + i * BAR / 4, 0.3)
            continue
        # ---- LIFE FLASH (bar 20): total vacuum ----
        if bar == 20:
            tail = pitch_shift(lines["evez"], 2 ** (5 / 12) * 2)
            M.add(envelope(tail), t0 + BAR / 2, 0.5, 0.8)
            M.add(halo[:int(BAR * SR)], t0, 0.0, 0.35)  # one held choir note
            continue
        # ---- DEMONS RISING (4-11): reese + half-time kick + metal ----
        if 4 <= bar <= 11:
            r = reese(BASE_D3 / 4, BAR)
            M.add(r, t0, 0.0, 0.95)
            for half in range(2):  # half-time kick = 98 feel
                M.add(kick(), t0 + half * BAR / 2, 0.0)
            if bar % 2 == 0:
                M.add(metal_hit(), t0 + BAR * 0.75, -0.5)
            M.add(demon["sealed"] if bar % 2 else demon["witness"], t0 + BAR / 4, 0.4, 0.6)
            M.add(halo[:int(BAR * SR)], t0, -0.3, 0.22)  # angel watching from above
            continue
        # ---- TEMPO COLLAPSE (12-19) / UNION (21-31): full grid ----
        union = 21 <= bar <= 31
        ascending = 32 <= bar <= 39
        if ascending:
            M.add(riser(BAR * 1.5), t0, 0.0, 0.5)
            roll_n = 8 + (bar - 32) * 4  # accelerating 64th micro-rolls
            for k in range(roll_n):
                M.add(snare(0.04, 1500 + k * 60, 3200, seed=bar * 100 + k),
                      t0 + k * BAR / roll_n, 0.6 if k % 2 else -0.6, 0.5)
            if bar >= 38:
                M.add(supersaw(BASE_D3 * 2.5, BAR, gain_env := 1), t0, -0.3, 0.5)
            continue
        # full breakcore grid: 16th hats + necklace snare + 64th micro-roll ends
        for s16 in range(16):
            at = t0 + s16 * sixteenth
            if seed16[s16]:
                if s16 % 4 == 0:
                    M.add(kick(), at, 0.0)
                else:
                    M.add(snare(), at, -0.45)
            if s16 % 2 == 0:
                n = bandpass_noise(0.03, 6000, 11000, seed=bar + s16)
                ttt = np.arange(len(n)) / SR
                M.add(n * np.exp(-ttt / 0.008) * 0.5, at, 0.45)
        if bar % 2 == 1:
            for k in range(8):  # 64th micro-roll = 392 BPM feel
                M.add(snare(0.035, 1600 + k * 90, 3600, seed=900 + bar * 10 + k),
                      t0 + BAR - sixteenth * 2 + k * sixteenth / 2, 0.55 if k % 2 else -0.55, 0.55)
        # the binary: angel supersaw theme (fwd) vs demon bitcrush (retrograde)
        fwd = CRAB[bar % 8]
        inv = (7 - CRAB[7 - (bar % 8)]) % 8
        lift = 2 ** ((bar - 21) * 0.02) if union else 1.0  # slow ascent
        angel_f = BASE_D3 * HIJAZ[fwd] * 2 * lift
        M.add(supersaw(angel_f, BAR * 0.6), t0 + BAR / 8, -0.6, 0.42)
        dem = np.round(ks_note(BASE_D3 * HIJAZ[inv] * 0.5, 0.4, 0.990) * 8) / 8
        M.add(envelope(dem), t0 + BAR / 4, 0.65, 0.5)
        M.add(halo[:int(BAR * SR)], t0, 0.0, 0.3)  # the choir never stops
        if union and bar % 2 == 1:
            g = lines["evez"][int(SR * 0.05): int(SR * 0.05) + int(SR * 0.15)]
            M.add(envelope(g.copy()), t0 + BAR / 2, -0.6, 0.75)
            M.add(envelope(pitch_shift(g, 2 ** (5 / 12))), t0 + BAR / 2 + sixteenth, 0.6, 0.6)

    # ---- master ----
    L, R = M.L, M.R
    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) or 1.0
    L, R = L / peak * 0.85, R / peak * 0.85
    L, R = np.tanh(L * 1.3), np.tanh(R * 1.3)
    n = min(len(L), len(R))
    edge = int(SR * 0.05)
    for ch in (L, R):
        ch[:edge] *= np.linspace(0, 1, edge)
        ch[-edge:] *= np.linspace(1, 0, edge)
    stereo = np.stack([L[:n], R[:n]], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"RENDERED {a.out}: {n/SR:.2f}s @ {BPM} BPM, {bars} bars")
    print(f"halo choir length {len(halo)/SR:.1f}s | life-flash vacuum @ {20*BAR:.2f}s | ascent @ {32*BAR:.2f}s")
    print(f"L/R correlation {np.corrcoef(L,R)[0,1]:.4f} (angel/demon split)")


if __name__ == "__main__":
    main()
