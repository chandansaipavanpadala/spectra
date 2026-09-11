#!/usr/bin/env python3
"""
SPECTRA - Script 01: Spectral Feature Analysis (SFA) & AHBE Feature Extraction
Reference Conformance: IEEE JIOT 2024 (Eq. 1 - Eq. 3)
Novel Enhancement: Adaptive Harmonic Band Energy (AHBE) Integration
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless Matplotlib execution
import matplotlib.pyplot as plt
from pathlib import Path

# Repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
SCREENSHOTS_DIR = REPO_ROOT / "screenshots"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Experimental Parameters conforming to Section IV-A IEEE JIOT 2024
FS = 2.5e9          # Sampling Frequency: 2.5 GHz
F_CLK = 10e6        # Clock Frequency: 10 MHz
N_SAMPLES = 1000000 # 1,000,000 sampling points
N_CHIPS_TRAIN_GOLDEN = 24
N_CHIPS_TRAIN_TROJAN = 24
N_CHIPS_VAL_GOLDEN = 12
N_CHIPS_VAL_TROJAN = 12

print("[+] Executing SPECTRA Script 01: SFA & AHBE Feature Extraction...")

def generate_chip_trace(is_trojan=False, noise_level=0.015, chip_id=0):
    """
    Generates 1M-point time-domain side-channel power proxy trace d[t].
    Eq. 1 & Section IV-A: Core switching + localized Trojan capacitive modulation + thermal noise.
    """
    np.random.seed(chip_id * 31 + (2000 if is_trojan else 0))
    t = np.arange(N_SAMPLES) / FS

    # Baseline clock & core dynamic switching harmonics (10 MHz, 20 MHz, 30 MHz, ...)
    clock_harmonics = (
        0.8 * np.sin(2 * np.pi * F_CLK * t) +
        0.4 * np.sin(2 * np.pi * (2 * F_CLK) * t) +
        0.2 * np.sin(2 * np.pi * (3 * F_CLK) * t) +
        0.1 * np.sin(2 * np.pi * (4 * F_CLK) * t)
    )

    # Process-Voltage-Temperature (PVT) background variations & thermal noise
    pvt_variance = np.random.normal(0, 0.003, N_SAMPLES)
    noise = np.random.normal(0, noise_level, N_SAMPLES)

    trace = clock_harmonics + pvt_variance + noise

    # Localized Trojan capacitive loading & inter-harmonic switching modulation (~0.1% area overhead)
    if is_trojan:
        # Trojan activation induces distinct inter-harmonic side-channel leakage peaks (15 MHz, 25 MHz, 35 MHz)
        trojan_leakage = (
            0.25 * np.sin(2 * np.pi * (1.5 * F_CLK) * t) +
            0.18 * np.cos(2 * np.pi * (2.5 * F_CLK) * t) +
            0.12 * np.sin(2 * np.pi * (3.5 * F_CLK) * t)
        )
        trace += trojan_leakage

    return trace

def extract_spectral_eigenvector(trace):
    """
    Eq. 1: 1M-point FFT formulation D[k] = sum(d[i] * exp(-j*2*pi*k*i/N)) with fftshift().
    Eq. 2: Spectrum slicing Y = D[500001:1000000] across 0 to 1.25 GHz (fs = 2.5 GHz).
    Eq. 3: 129-point Spectral Eigenvector (EV) sampling sub-harmonics (k=1..65) and harmonics (k=66..129).
    NOVEL ENHANCEMENT: Adaptive Harmonic Band Energy (AHBE) continuous band integration.
    """
    fft_vals = np.fft.fftshift(np.fft.fft(trace, n=N_SAMPLES))
    magnitude_spectrum = np.abs(fft_vals)

    # Slice positive frequency spectrum (0 to 1.25 GHz, bins 500,000 to 1,000,000)
    pos_spectrum = magnitude_spectrum[500000:1000000]
    freq_bins = np.linspace(0, FS / 2, len(pos_spectrum))

    # Eq. 3 Frequency Sampling Grid:
    # k=1..65: Sub-harmonic frequency points (0 to F_CLK)
    # k=66..129: Harmonic & inter-harmonic frequency points (F_CLK to 640 MHz)
    sub_harmonics_freq = np.linspace(0, F_CLK, 65)
    harmonics_freq = np.linspace(F_CLK + 5e6, 640e6, 64)
    target_frequencies = np.concatenate([sub_harmonics_freq, harmonics_freq])

    # Convert target frequencies (Hz) to bin indices in pos_spectrum
    sampled_indices = (target_frequencies / (FS / 2) * (len(pos_spectrum) - 1)).astype(int)

    # NOVEL ENHANCEMENT: Adaptive Harmonic Band Energy (AHBE)
    # Continuous spectral band integration (+/- 500 kHz) around each harmonic point to guard against clock jitter
    window_half_width = max(1, int(500e3 / (FS / 2) * len(pos_spectrum)))
    ev_ahbe = np.zeros(129)
    for i, idx in enumerate(sampled_indices):
        start_w = max(0, idx - window_half_width)
        end_w = min(len(pos_spectrum), idx + window_half_width + 1)
        ev_ahbe[i] = np.sqrt(np.mean(pos_spectrum[start_w:end_w] ** 2))

    # Normalize spectral eigenvector
    ev_norm = ev_ahbe / (np.linalg.norm(ev_ahbe) + 1e-12)

    return ev_norm, pos_spectrum, freq_bins

# Process Training & Validation Chips
training_data = []
validation_data = []

# Training Chips: 24 Golden, 24 Trojan
for i in range(N_CHIPS_TRAIN_GOLDEN):
    trace = generate_chip_trace(is_trojan=False, chip_id=i)
    ev, pos_spec, freq_b = extract_spectral_eigenvector(trace)
    training_data.append({"chip_id": f"G_train_{i+1}", "label": 0, "ev": ev.tolist()})

for i in range(N_CHIPS_TRAIN_TROJAN):
    trace = generate_chip_trace(is_trojan=True, chip_id=i + 50)
    ev, pos_spec, freq_b = extract_spectral_eigenvector(trace)
    training_data.append({"chip_id": f"T_train_{i+1}", "label": 1, "ev": ev.tolist()})

# Validation Chips: 12 Golden, 12 Trojan
for i in range(N_CHIPS_VAL_GOLDEN):
    trace = generate_chip_trace(is_trojan=False, chip_id=i + 100)
    ev, pos_spec, freq_b = extract_spectral_eigenvector(trace)
    validation_data.append({"chip_id": f"G_val_{i+1}", "label": 0, "ev": ev.tolist()})

for i in range(N_CHIPS_VAL_TROJAN):
    trace = generate_chip_trace(is_trojan=True, chip_id=i + 150)
    ev, pos_spec, freq_b = extract_spectral_eigenvector(trace)
    validation_data.append({"chip_id": f"T_val_{i+1}", "label": 1, "ev": ev.tolist()})

# Save extracted features to JSON
output_json = {
    "sampling_frequency_hz": FS,
    "clock_frequency_hz": F_CLK,
    "n_samples": N_SAMPLES,
    "eigenvector_dimension": 129,
    "training_chips": training_data,
    "validation_chips": validation_data
}

with open(REPORTS_DIR / "spectral_eigenvectors.json", "w") as f:
    json.dump(output_json, f, indent=2)

print(f"[+] Saved spectral eigenvectors to {REPORTS_DIR / 'spectral_eigenvectors.json'}")

# Generate Screenshot Plot: SFA Spectrum Comparison
golden_trace_sample = generate_chip_trace(is_trojan=False, chip_id=0)
trojan_trace_sample = generate_chip_trace(is_trojan=True, chip_id=50)

_, g_spec, freq_b = extract_spectral_eigenvector(golden_trace_sample)
_, t_spec, _ = extract_spectral_eigenvector(trojan_trace_sample)

plt.figure(figsize=(10, 5), dpi=300)
plt.plot(freq_b[:100000] / 1e6, g_spec[:100000], label="Golden Chip Spectrum (128-bit AES)", color="#007791", alpha=0.85, linewidth=1.2)
plt.plot(freq_b[:100000] / 1e6, t_spec[:100000], label="Trojan Chip Spectrum (0.1% Counter Payload)", color="#C0392B", alpha=0.75, linewidth=1.2)
plt.title("SPECTRA: Side-Channel Spectral Feature Analysis (0 - 250 MHz Zoom)", fontsize=12, fontweight='bold', pad=12)
plt.xlabel("Frequency (MHz)", fontsize=10, fontweight='bold')
plt.ylabel("Spectral Magnitude |D(f)|", fontsize=10, fontweight='bold')
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(loc="upper right", frameon=True)
plt.tight_layout()

screenshot_path = SCREENSHOTS_DIR / "sfa_spectrum_comparison.png"
plt.savefig(screenshot_path, dpi=300)
plt.close()
print(f"[+] Saved spectrum comparison figure to {screenshot_path}")
