"""
Generate the safe-to-operate sweep with RANDOM loss rates:  STO-random_decay-200k.csv

Same experiment as STO_ESC_randdecay.m, run with the Python simulator
(Tools/esc_sim.py, validated against the MATLAB datasets):
  * constant plant per run, but the confinement times are drawn per run:
        tau_D = 1.71 +- 0.1 s,   tau_T = 1.66 +- 0.1 s   (uniform)
  * ESC parameters drawn exactly as in STO_ESC_constdecay.m:
        optimizer_gain   log-uniform in [1e-5, 5]
        dither_amplitude uniform in (0, 1]
        dither_frequency uniform in (0, 10] Hz
  * r_hat starts at 0; converged = within 5 % of the ideal ratio for 5 s.
The drawn loss rates and the resulting ideal ratio are stored for every run.

Usage (from anywhere):
    python generate_STO_random_decay.py [n_runs] [seed]
"""
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = next(p for p in [HERE] + [os.path.abspath(os.path.join(HERE, *[".."] * i)) for i in range(1, 6)]
            if os.path.isdir(os.path.join(p, "Tools")))
sys.path.insert(0, os.path.join(ROOT, "Tools"))
from esc_sim import simulate_in_chunks
from esc_paths import data_folder

N_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
OUT = os.path.join(str(data_folder("STO-random_decay")), f"STO-random_decay-{N_RUNS // 1000}k.csv")

rng = np.random.default_rng(SEED)
optimizer_gain = 10 ** rng.uniform(np.log10(1e-5), np.log10(5), N_RUNS)
dither_amplitude = 1 - rng.uniform(0, 1, N_RUNS)        # uniform in (0, 1]
dither_frequency = 10 * (1 - rng.uniform(0, 1, N_RUNS))  # uniform in (0, 10]
tau_D = 1.71 + (rng.uniform(0, 1, N_RUNS) - 0.5) * 0.2   # +- 0.1 s
tau_T = 1.66 + (rng.uniform(0, 1, N_RUNS) - 0.5) * 0.2   # +- 0.1 s

t0 = time.time()
sim = simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                         tau_D=tau_D, tau_T=tau_T, r_hat_0=0.0)
df = pd.DataFrame({
    "optimizer_gain": optimizer_gain,
    "dither_amplitude": dither_amplitude,
    "dither_frequency": dither_frequency,
    "n_D_decay_rate": 1 / tau_D,
    "n_T_decay_rate": 1 / tau_T,
    "ideal_ratio": sim["ideal_ratio"],
    "converged": sim["converged"].astype(int),
    "convergence_time": sim["convergence_time"],
})
df.to_csv(OUT, index=False, na_rep="NaN")
print(f"{N_RUNS} runs in {time.time() - t0:.0f} s (seed {SEED}) -> {OUT}")
print(f"converged: {df.converged.mean():.4f} | ideal ratio range: {df.ideal_ratio.min():.4f}-{df.ideal_ratio.max():.4f}")
