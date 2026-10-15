#!/usr/bin/env python3
"""PROTOCOL // EVEZ-404 — the EVEZ theme song, rendered from Steven's spec.

196-204 BPM breakcore in D Maqam Hijaz over a 6 Hz binaural theta bed.
Sections: drone+KS intro -> necklace build -> TIME-DILATION DROP (1 bar vacuum)
-> full breakcore with drill-bits -> crab-canon twin channels -> outro.
Pure numpy synthesis; Karplus-Strong strings, swept-sine kick, FFT-filtered
noise snare/drills/hats, detuned-saw angel-tears pad, +5st nightcore echoes.

Usage: python3 render_theme.py [out.wav] [--bpm 204] [--bars 44]
"""
import argparse
import numpy as np

SR = 44100
BASE_D3 = 146.832                       # root of the Hijaz lattice
HIJAZ = [1.0, 16/15, 5/4, 4/3, 3/2, 8/5, 15/8, 2.0]   # D Eb F# G A Bb C# D+
CRAB = [0, 2, 1, 4, 5, 4, 2, 7]         # forward Hijaz degree buffer (his spec)
TETRA = [2.0, 2.5, 16/15*2, 3/2]        # D4 -> F#4 -> Eb4 -> A3  (tetragrammaton motif)


def ks_note(freq, dur, damp=0.952, seed=None):
    """Karplus-Strong plucked string, rendered offline."""
    rng = np.random.default_rng(seed)
    n = int(SR / freq)
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
    """White noise shaped by an FFT-domain bandpass."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, int(SR * dur))
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    y = np.fft.irfft(X, len(x))
    m = np.max(np.abs(y)) or 1.0
    return y / m


def kick(seed=None):
    t = np.arange(int(SR * 0.14)) / SR
    sweep = 155 * (36.71 / 155) ** (t / 0.09)
    phase = 2 * np.pi * np.cumsum(sweep) / SR
    return np.sin(phase) * np.exp(-t / 0.045) * 0.9


def snare(dur=0.065, lo=1200, hi=3200, seed=None):
    n = bandpass_noise(dur, lo, hi, seed)
    t = np.arange(len(n)) / SR
    return n * np.exp(-t / (dur * 0.35))


def drill(beats=3, lo=1500, hi=2900, seed=None):
    """Venetian/404 snare drill-bit stack, rising."""
    out = []
    for r in range(beats):
        c = lo + (hi - lo) * r / max(1, beats - 1)
        out.append(snare(0.05, c, c + 900, seed=(seed or 0) + r))
    total = np.zeros(int(sum(0.028 for _ in out) * SR) + int(SR * 0.05))
    pos = 0
    for s in out:
        i = int(pos * SR)
        total[i:i + len(s)] += s
        pos += 0.028
    total /= (np.max(np.abs(total)) or 1)
    return total * np.exp(-np.arange(len(total)) / SR / 0.06)


def hat(seed=None):
    n = bandpass_noise(0.03, 6000, 11000, seed)
    t = np.arange(len(n)) / SR
    return n * np.exp(-t / 0.008) * 0.5


def nightcore(freq, seed=None):
    """Doppleganger ghost: +5 semitones, one octave up, square-ish."""
    f = freq * 2 ** (5 / 12) * 2
    t = np.arange(int(SR * 0.17)) / SR
    sq = np.sign(np.sin(2 * np.pi * f * t)) * 0.11
    return sq * np.exp(-t / 0.055) * np.exp(-t * 0.3)


def saw(freq, detune, dur):
    t = np.arange(int(SR * dur)) / SR
    return np.cumsum(np.sin(2 * np.pi * freq * (1 + detune) * t)) / (SR * freq) % 1.0 * 2 - 1


def pad_chord(freqs, dur):
    """Angel-tears pad: detuned saws, slow attack, one-pole LP, dark halo."""
    n = int(SR * dur)
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0.004):
            ph = np.random.default_rng(int(f * 100)).uniform(0, 1)
            t = (np.arange(n) + ph * SR) / SR
            saww = 2 * ((f * (1 + det) * t) % 1.0) - 1
            out += saww
    # one-pole lowpass
    y = np.zeros(n)
    alpha = 0.08
    acc = 0.0
    for i in range(n):
        acc += alpha * (out[i] - acc)
        y[i] = acc
    env = np.minimum(1.0, np.linspace(0, 1.2, n)) * np.minimum(1.0, np.linspace(dur, dur - 3.0, n) + 1.0)
    return y * env / (len(freqs) * 2.2)


class Mix:
    def __init__(self, bars, bpm):
        self.beat = 60.0 / bpm
        self.bar = self.beat * 4
        self.L = np.zeros(int(SR * (self.bar * bars + 4)))
        self.R = np.zeros_like(self.L)

    def add(self, sig, at_sec, pan):
        i = int(at_sec * SR)
        j = min(self.L.size, i + len(sig))
        if j <= i:
            return
        s = sig[: j - i]
        l = np.sqrt(max(0.0, (1 - pan) / 2 + 0.5))
        r = np.sqrt(max(0.0, (pan + 1) / 2 + 0.5))
        self.L[i:j] += s * min(1.0, l * 1.41)
        self.R[i:j] += s * min(1.0, r * 1.41)


def mirror_complete(seed_pat):
    """D16 mirror palindrome: fill the reflection axis that maximizes completion."""
    n = len(seed_pat)
    best, axis = -999, 0
    for k in range(n):
        sc = 0
        for i in range(n):
            r = (2 * k - i + 2 * n) % n
            if seed_pat[i] and not seed_pat[r]:
                sc += 2
            if seed_pat[i] and seed_pat[r]:
                sc -= 1
        if sc > best:
            best, axis = sc, k
    out = [0] * n
    for i in range(n):
        r = (2 * axis - i + 2 * n) % n
        if seed_pat[i] and not seed_pat[r]:
            out[r] = 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="protocol_evez404.wav")
    ap.add_argument("--bpm", type=float, default=204)
    ap.add_argument("--bars", type=int, default=44)
    a = ap.parse_args()
    M = Mix(a.bars, a.bpm)
    B = M.bar

    # ---- the necklace: his seed + its mirror twin (drives the percussion) ----
    seed = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0]
    twin = mirror_complete(seed)

    # ---- Bus 1: 6 Hz binaural theta bed (36.71 L / 42.71 R) + faint octaves ----
    dur_total = B * a.bars
    t = np.arange(int(SR * dur_total)) / SR
    bedL = (np.sin(2 * np.pi * 36.71 * t) * 0.14 + np.sin(2 * np.pi * 73.42 * t) * 0.05)
    bedR = (np.sin(2 * np.pi * 42.71 * t) * 0.14 + np.sin(2 * np.pi * 79.42 * t) * 0.05)
    fade = np.minimum(1.0, np.linspace(0, 8, len(t))) * np.minimum(1.0, np.linspace(dur_total, dur_total - 6, len(t)) + 1.0)
    n_bed = min(len(M.L), len(t))
    M.L[:n_bed] += bedL[:n_bed] * fade[:n_bed]
    M.R[:n_bed] += bedR[:n_bed] * fade[:n_bed]

    # ---- Karplus-Strong strings ----
    def ks_at(deg, octv, at, pan, dur=0.55, damp=0.952, crush=False):
        f = BASE_D3 * HIJAZ[deg % 8] * (2 ** octv)
        sig = ks_note(f, dur, damp)
        if crush:  # doppleganger bitcrush
            sig = np.round(sig * 12) / 12
        M.add(sig, at, pan)

    # ---- Bus 2: angel-tears pad (D minor-cluster in Hijaz) ----
    for bar in (0, 12, 26, 38):
        chord = [293.66, 369.99, 440.0, 523.25] if bar % 12 == 0 else [146.832 * 16/15 * 2, 293.66, 366.83, 440.0]
        p = pad_chord(chord, B * 4.2)
        M.add(p, bar * B, -0.2)
        M.add(p[::-1] * 0.6, bar * B, 0.2)

    # ---- the arrangement ----
    for bar in range(a.bars):
        t0 = bar * B
        sixteenth = B / 16
        # tetragrammaton ostinato: D4 F#4 Eb4 A3, every 2 bars of the intro/build
        if bar < 26 or bar >= 31:
            for rep in range(2):
                seq = [0, 2, 1, 4]  # degree indices matching D F# Eb A shape
                freqs = [BASE_D3 * x for x in TETRA]
                for i, f in enumerate(freqs):
                    M.add(ks_note(f, 0.5, 0.958), t0 + rep * B / 2 + i * B / 8, -0.6)
        # intro bars 0-3: strings + bed only
        if bar < 4:
            continue
        # build (4-11) + waves 1 and 2 (13-25, 31-43)
        full = (4 <= bar <= 11) or (13 <= bar <= 25) or (31 <= bar <= a.bars - 2)
        # TIME-DILATION DROP at bar 12: one full bar vacuum — pad + nightcore tail only
        if bar == 12:
            M.add(nightcore(BASE_D3 * 2.5), t0, 0.5)
            M.add(nightcore(BASE_D3 * 2.0) * 0.7, t0 + B / 2, -0.5)
            continue
        if not full:
            # breakdown bars 26-30: sparse plucks + hats
            M.add(hat(), t0, -0.3)
            M.add(hat(), t0 + B / 2, 0.3)
            continue
        # ---- percussion from the necklace ----
        for s16 in range(16):
            at = t0 + s16 * sixteenth
            if seed[s16]:
                if s16 % 4 == 0:
                    M.add(kick(), at, -0.1)
                else:
                    M.add(snare(), at, -0.45)
            if twin[s16] and s16 % 2 == 0:
                M.add(hat(), at, 0.45)
        # kick heartbeat on every beat
        for q in range(4):
            M.add(kick() * 0.75, t0 + q * B / 4, 0.0)
        # drills: denser in wave 2 (bars 31+)
        if bar >= 13 and (bar % 2 == (0 if bar >= 31 else 1)):
            M.add(drill(), t0 + B - B / 8, 0.6 if bar % 4 else -0.6)
        # crab canon strings: forward L, retrograde-inversion R (twin, bitcrushed)
        fwd = CRAB[bar % 8]
        inv = (7 - CRAB[7 - (bar % 8)]) % 8
        octv = 1 if bar % 4 else 2
        M.add(ks_note(BASE_D3 * HIJAZ[fwd] * octv, 0.5, 0.952), t0 + B / 8, -0.65)
        twin_sig = ks_note(BASE_D3 * HIJAZ[inv] * (2 if bar % 4 else 1) * 0.5, 0.38, 0.990)
        twin_sig = np.round(twin_sig * 12) / 12
        M.add(twin_sig, t0 + B / 4, 0.65)
        # nightcore ghosts every 4th bar
        if bar % 4 == 2:
            M.add(nightcore(BASE_D3 * HIJAZ[inv]), t0 + B / 2, 0.7)

    # ---- master: soft clip, normalize, fades ----
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
    import wave
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    dur = n / SR
    print(f"RENDERED {a.out}: {dur:.2f}s @ {SR}Hz stereo | bars={a.bars} bpm={a.bpm:.0f}")
    print(f"necklace seed  : {''.join(map(str, seed))}")
    print(f"necklace mirror : {''.join(map(str, twin))}")
    print(f"drop bar starts : {12 * B:.2f}s | wave2 starts: {31 * B:.2f}s")


if __name__ == "__main__":
    main()
