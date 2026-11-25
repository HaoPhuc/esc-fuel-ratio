"""
Python version of STO_ESC_randdecay.m

Safe to operate, random loss rates: as STO_ESC_constdecay, but every trial draws its own loss times,
1.71 +- 0.1 s (D) and 1.66 +- 0.1 s (T). Output columns: optimizer_gain, dither_amplitude,
dither_frequency, n_D_decay_rate, n_T_decay_rate, ideal_ratio, converged, convergence_time.

This file follows the MATLAB script draw for draw. The data set in this folder,
STO-random_decay-200k.csv, was made earlier with generate_STO_random_decay.py: the same experiment,
but with a different random generator, so the two files do not contain the same parameter sets.

The simulation is not repeated in this file: it is in Tools/esc_sim.py, which follows the MATLAB loop
step for step and simulates many parameter sets at once. The convergence rule (r_hat within 5 % of the
ideal ratio for 5 s) and the model constants are set there.

Usage
    python STO_ESC_randdecay.py                                   200,000 runs
    python STO_ESC_randdecay.py --combinations 1000 --output test.csv
The default file name ends in "-python", so existing data sets are never replaced by accident.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402  (the simulation, checked against the MATLAB data sets)
import esc_sweeps as sweeps    # noqa: E402  (random numbers and file output as in MATLAB)
import esc_paths as paths      # noqa: E402  (where the data folder is)

# ---- Batch sweep settings ----------------------------------------------------
combinations = 200_000          # total random sets to test
seed = 0                        # 0 = the random numbers of a freshly started MATLAB

# ---- Simulation settings ------------------------------------------------------
tend = 100                      # [s]
dt = 0.01                       # [s]
r_hat_0 = 0                     # ESC starting fuel ratio

# ---- ESC parameter ranges (same as STO_ESC_constdecay) --------------------------
dither_amplitude_range = (0, 1)
dither_frequency_range = (0, 10)
optimizer_gain_range = (1e-5, 5)

# ---- Loss times: nominal value +- 0.1 s ---------------------------------------------
tau_D_nominal = 1.71            # [s]
tau_T_nominal = 1.66            # [s]
tau_spread = 0.2                # full width of the uniform spread [s]


def main():
    args = sweeps.arguments(__doc__, combinations, seed)
    output = sweeps.output_path(paths.data_folder('STO-random_decay'), f'STO-random_decay-{sweeps.count_label(args.combinations)}-python.csv', args)

    # One MATLAB trial calls rand() in this order (the two loss rates are drawn inside esc_trial)
    u = sweeps.draw(sweeps.matlab_rng(args.seed, args.skip), args.combinations,
                    ['dither_amplitude', 'dither_frequency', 'optimizer_gain', 'n_D_decay_rate', 'n_T_decay_rate'])
    dither_amplitude = sweeps.uniform(dither_amplitude_range, u['dither_amplitude'])
    dither_frequency = sweeps.uniform(dither_frequency_range, u['dither_frequency'])
    optimizer_gain = sweeps.log_uniform(optimizer_gain_range, u['optimizer_gain'])   # randomize the power
    tau_D = tau_D_nominal + (u['n_D_decay_rate'] - 0.5) * tau_spread                 # +- 0.1
    tau_T = tau_T_nominal + (u['n_T_decay_rate'] - 0.5) * tau_spread                 # +- 0.1

    # Run all trials
    trial = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                                   tau_D=tau_D, tau_T=tau_T, r_hat_0=r_hat_0, dt=dt, tend=tend,
                                   progress='ESC trials')

    results = pd.DataFrame({
        'optimizer_gain': optimizer_gain,
        'dither_amplitude': dither_amplitude,
        'dither_frequency': dither_frequency,
        'n_D_decay_rate': 1 / tau_D,
        'n_T_decay_rate': 1 / tau_T,
        'ideal_ratio': trial['ideal_ratio'],
        'converged': trial['converged'],
        'convergence_time': trial['convergence_time'],
    })
    sweeps.write_csv(results, output)
    print(f"converged: {results['converged'].mean():.4f}")


if __name__ == '__main__':
    main()
