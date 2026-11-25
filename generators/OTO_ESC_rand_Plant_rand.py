"""
Python version of OTO_ESC_rand_Plant_rand.m

Optimal to operate: random ESC parameters on random plants. The ideal ratio drifts as
r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t). Every trial is run twice: with ESC (r_hat starts at 0.5)
and with the fuel ratio fixed at 0.5.
Output columns: optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, energy_ESC,
energy_const, energy_max, choose_ESC, converged, convergence_time.

With the default seed, the first rows are the rows of OTO-ESC-200k.csv (the MATLAB data set).

The simulation is not repeated in this file: it is in Tools/esc_sim.py, which follows the MATLAB loop
step for step and simulates many parameter sets at once. The convergence rule (r_hat within 5 % of the
ideal ratio for 5 s) and the model constants are set there.

Usage
    python OTO_ESC_rand_Plant_rand.py                             200,000 runs
    python OTO_ESC_rand_Plant_rand.py --combinations 1000 --output test.csv
The default file name ends in "-python", so the MATLAB data set is never replaced by accident.
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
r_hat_0 = 0.5                   # ESC starting fuel ratio
const_ratio = 0.5               # fixed fuel ratio without ESC

# ---- ESC parameter ranges -----------------------------------------------------
optimizer_gain_range = (1e-5, 5)
dither_amplitude_range = (0, 1)
dither_frequency_range = (0, 10)

# ---- Ideal fuel ratio ranges: r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t) --------
r_ideal_0_range = (0.45, 0.55)
lambda_r_ideal_range = (-0.002, 0.002)   # [1/s]


def main():
    args = sweeps.arguments(__doc__, combinations, seed)
    output = sweeps.output_path(paths.data_folder('OTO-ESC'), f'OTO-{sweeps.count_label(args.combinations)}shots-python.csv', args)

    # One MATLAB trial calls rand() in this order
    u = sweeps.draw(sweeps.matlab_rng(args.seed, args.skip), args.combinations,
                    ['dither_amplitude', 'dither_frequency', 'optimizer_gain', 'r_ideal_0', 'lambda_r_ideal'])
    # ESC parameters (randomized)
    dither_amplitude = sweeps.uniform(dither_amplitude_range, u['dither_amplitude'])
    dither_frequency = sweeps.uniform(dither_frequency_range, u['dither_frequency'])
    optimizer_gain = sweeps.log_uniform(optimizer_gain_range, u['optimizer_gain'])   # randomize the power
    # Ideal fuel ratio (randomized)
    r_ideal_0 = sweeps.uniform(r_ideal_0_range, u['r_ideal_0'])
    lambda_r_ideal = sweeps.uniform(lambda_r_ideal_range, u['lambda_r_ideal'])

    # Run the trials: with ESC, and with the fixed fuel ratio on the same plants
    esc = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                                 r_ideal_0=r_ideal_0, lambda_r_ideal=lambda_r_ideal, r_hat_0=r_hat_0,
                                 dt=dt, tend=tend, progress='ESC trials')
    fixed = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                                   r_ideal_0=r_ideal_0, lambda_r_ideal=lambda_r_ideal,
                                   use_esc=False, fixed_ratio=const_ratio,
                                   dt=dt, tend=tend, progress='fixed-ratio trials')

    results = pd.DataFrame({
        'optimizer_gain': optimizer_gain,
        'dither_amplitude': dither_amplitude,
        'dither_frequency': dither_frequency,
        'r_ideal_0': r_ideal_0,
        'lambda_r_ideal': lambda_r_ideal,
        'energy_ESC': esc['energy'],
        'energy_const': fixed['energy'],
        # theoretical maximum: n_D = n_T = n_ref/2 the whole time (same for every case)
        'energy_max': 0.25 * sim.N_REF ** 2 * tend,
        # should we choose ESC? (1 = ESC gives more energy than the fixed ratio)
        'choose_ESC': (esc['energy'] > fixed['energy']).astype(int),
        'converged': esc['converged'],
        'convergence_time': esc['convergence_time'],
    })
    sweeps.write_csv(results, output)
    print(f"choose_ESC: {results['choose_ESC'].mean():.4f}   converged: {results['converged'].mean():.4f}")


if __name__ == '__main__':
    main()
