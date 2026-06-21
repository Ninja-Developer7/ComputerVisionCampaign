#!/usr/bin/env python3
"""
Cyberpunk soundtrack synthesizer.
Generates a 60-second cyberpunk/synthwave audio track.
"""
import numpy as np
from scipy.io import wavfile
import os

SAMPLE_RATE = 44100
DURATION = 60
OUTPUT_PATH = "/Users/ronin/episode_builder/audio/soundtrack.wav"

def make_bass_drone(t):
    # Deep pulsing bass at ~55 Hz with slow amplitude modulation
    freq = 55.0
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t)
    bass = 0.3 * np.sin(2 * np.pi * freq * t) * lfo
    # Add a subtle sub-octave
    bass += 0.2 * np.sin(2 * np.pi * (freq/2) * t) * lfo
    return bass

def make_arp(t):
    # 16th note arpeggiated sawtooth-like synth line
    # Using a minor pentatonic scale in A minor: A, C, D, E, G
    notes = [220.0, 261.63, 293.66, 329.63, 392.0]  # A3, C4, D4, E4, G4
    bpm = 128
    beat_samples = int(SAMPLE_RATE * 60 / bpm)
    sixteenth = beat_samples // 4
    n_samples = len(t)
    arp = np.zeros(n_samples)
    
    # Create pattern using pentatonic scale indices (0-4)
    pattern = [0, 2, 4, 2, 3, 1, 3, 1, 0, 2, 4, 3, 2, 1, 0, 0]
    note_idx = 0
    for i in range(0, n_samples, sixteenth):
        end_i = min(i + sixteenth, n_samples)
        envelope = np.ones(end_i - i)
        # Fast attack, medium decay
        attack = min(128, end_i - i)
        envelope[:attack] = np.linspace(0, 1, attack)
        decay = max(0, end_i - i - attack)
        envelope[attack:] *= np.exp(-np.linspace(0, 4, decay))
        freq = notes[pattern[note_idx % len(pattern)]]
        # Sawtooth-ish wave
        phase = 2 * np.pi * freq * t[i:end_i]
        wave = 2 * (phase / (2*np.pi) - np.floor(0.5 + phase / (2*np.pi)))
        # Low-pass effect via simple averaging (crude)
        wave = np.convolve(wave, np.ones(3)/3, mode='same')
        arp[i:end_i] += 0.15 * wave * envelope
        note_idx += 1
    return arp

def make_pad(t):
    # Slowly evolving chord pad (Am: A2, C3, E3)
    freqs = [110.0, 130.81, 164.81]
    pad = np.zeros(len(t))
    for f in freqs:
        # Slow vibrato and amplitude modulation for movement
        mod = 0.6 + 0.4 * np.sin(2 * np.pi * (0.1 + 0.02*np.random.rand()) * t)
        phase = 2 * np.pi * (f + 0.5*np.sin(2*np.pi*5*t)) * t
        wave = np.sin(phase)
        pad += 0.12 * wave * mod
    return pad

def make_percussion(t):
    # High-hat and snare-ish electronic percussion
    bpm = 128
    beat_samples = int(SAMPLE_RATE * 60 / bpm)
    n_samples = len(t)
    perc = np.zeros(n_samples)
    
    for i in range(0, n_samples, beat_samples):
        # High hat on every 16th (simplified: every beat)
        if i < n_samples:
            end_i = min(i + int(beat_samples*0.1), n_samples)
            noise = np.random.randn(end_i - i)
            env = np.exp(-np.linspace(0, 10, end_i - i))
            # High-pass effect
            noise = np.convolve(noise, np.array([1, -1]), mode='same')
            perc[i:end_i] += 0.08 * noise * env
        
        # Kick on beat 0 and 2 of 4/4
        beat_in_bar = (i // beat_samples) % 4
        if beat_in_bar in [0, 2]:
            if i < n_samples:
                end_i = min(i + int(beat_samples*0.3), n_samples)
                k = np.arange(end_i - i)
                kick_env = np.exp(-k / (SAMPLE_RATE * 0.08))
                kick = 0.4 * np.sin(2 * np.pi * 150 * np.exp(-k/(SAMPLE_RATE*0.03)) * k / SAMPLE_RATE)
                # Actually simpler: sine dropping in freq
                kick_freq = np.linspace(120, 40, end_i - i)
                kick = 0.35 * np.sin(2 * np.pi * np.cumsum(kick_freq) / SAMPLE_RATE) * kick_env
                perc[i:end_i] += kick
    return perc

def make_rain_noise(t):
    # Colored noise for rain ambiance
    n = len(t)
    white = np.random.randn(n)
    # Simple low-pass via moving average
    window = 41
    rain = np.convolve(white, np.ones(window)/window, mode='same')
    # Amplitude modulation for gusty rain
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)
    return 0.06 * rain * gust

def synthesize():
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
    audio = np.zeros(len(t))
    
    print("Generating bass drone...")
    audio += make_bass_drone(t)
    
    print("Generating arpeggio...")
    audio += make_arp(t)
    
    print("Generating pad...")
    audio += make_pad(t)
    
    print("Generating percussion...")
    audio += make_percussion(t)
    
    print("Generating rain noise...")
    audio += make_rain_noise(t)
    
    # Soft master limiter
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9
    
    # Convert to 16-bit int
    audio_int = (audio * 32767).astype(np.int16)
    
    wavfile.write(OUTPUT_PATH, SAMPLE_RATE, audio_int)
    print(f"Soundtrack saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    synthesize()
