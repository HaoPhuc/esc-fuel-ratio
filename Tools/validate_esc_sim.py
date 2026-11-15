"""
Check the Python simulator (esc_sim.py) against the MATLAB-generated CSV files.

For a random sample of rows from each dataset, the same ESC parameters are
re-simulated in Python and compared with the stored MATLAB results.

Usage (from the repository root):
    python Tools/validate_esc_sim.py [rows_per_dataset]
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esc_sim import simulate_in_chunks

ROOT = os.environ.get("ESC_REPO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5000


def compare(name, ref, sim, energy_col=None, sim_energy=None):
    same_flag = (ref["converged"].astype(bool).values == sim["converged"])
    both = ref["converged"].astype(bool).values & sim["converged"]
    dt_conv = np.abs(ref["convergence_time"].values[both] - sim["convergence_time"][both])
    line = (f"{name:<34} rows {len(ref):>6} | converged flag equal {same_flag.mean():.4f} | "
            f"conv. time: max |diff| {dt_conv.max():.3g} s, equal within 0.01 s {np.mean(dt_conv < 0.0101):.4f}")
    if energy_col is not None:
        rel = np.abs(sim_energy - ref[energy_col].values) / np.abs(ref[energy_col].values)
        line += f" | {energy_col}: median rel. diff {np.median(rel):.2e}, 99th pct {np.quantile(rel, 0.99):.2e}"
    print(line)


# --- STO: constant plant, r_hat_0 = 0 ------------------------------------
path = os.path.join(ROOT, "Safe-to-operate", "STO-const_decay", "STO-const_decay-200k.csv")
ref = pd.read_csv(path).sample(N, random_state=0)
sim = simulate_in_chunks(ref.optimizer_gain, ref.dither_amplitude, ref.dither_frequency, r_hat_0=0.0)
compare("STO-const_decay-200k", ref, sim)

# --- OTO: drifting plant, r_hat_0 = 0.5, ESC and fixed r = 0.5 ----------
for fname in ["OTO-ESC-200k.csv", "OTO-ESC_fix-1_0.2_6-100kshots.csv", "OTO-Plant_fix-0.55_0.002-100kshots.csv"]:
    ref = pd.read_csv(os.path.join(ROOT, "Optimal-to-operate", fname)).sample(N, random_state=0)
    args = (ref.optimizer_gain, ref.dither_amplitude, ref.dither_frequency)
    plant = dict(r_ideal_0=ref.r_ideal_0.values, lambda_r_ideal=ref.lambda_r_ideal.values)
    sim = simulate_in_chunks(*args, r_hat_0=0.5, **plant)
    compare(fname.replace(".csv", ""), ref, sim, "energy_ESC", sim["energy"])
    const = simulate_in_chunks(*args, use_esc=False, fixed_ratio=0.5, **plant)
    rel = np.abs(const["energy"] - ref.energy_const.values) / ref.energy_const.values
    print(f"{'':<34} energy_const (fixed r = 0.5): max rel. diff {rel.max():.2e}")
