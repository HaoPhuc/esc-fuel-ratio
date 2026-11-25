"""
Python version of STO_ESC_constdecay.m

Safe to operate, constant plant: random ESC parameters, r_hat starts at 0, loss times 1.71 s (D) and
1.66 s (T). Output columns: optimizer_gain, dither_amplitude, dither_frequency, converged, convergence_time.

The simulation is not repeated in this file: it is in Tools/esc_sim.py, which follows the MATLAB loop
step for step and simulates many parameter sets at once. The convergence rule (r_hat within 5 % of the
ideal ratio for 5 s) and the model constants are set there.

Usage
    python STO_ESC_constdecay.py                                  200,000 runs
    python STO_ESC_constdecay.py --combinations 1000 --output test.csv
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
r_hat_0 = 0                     # ESC starting fuel ratio

# ---- ESC parameter ranges -----------------------------------------------------
optimizer_gain_range = (1e-5, 5)
dither_amplitude_range = (0, 1)
dither_frequency_range = (0, 10)


def main():
    args = sweeps.arguments(__doc__, combinations, seed)
    output = sweeps.output_path(paths.data_folder('STO-const_decay'), f'STO-const_decay-{sweeps.count_label(args.combinations)}-python.csv', args)

    # ESC parameters (randomized); one MATLAB trial calls rand() in this order
    u = sweeps.draw(sweeps.matlab_rng(args.seed, args.skip), args.combinations,
                    ['dither_amplitude', 'dither_frequency', 'optimizer_gain'])
    dither_amplitude = sweeps.uniform(dither_amplitude_range, u['dither_amplitude'])
    dither_frequency = sweeps.uniform(dither_frequency_range, u['dither_frequency'])
    optimizer_gain = sweeps.log_uniform(optimizer_gain_range, u['optimizer_gain'])   # randomize the power

    # Run all trials
    trial = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                                   r_hat_0=r_hat_0, dt=dt, tend=tend, progress='ESC trials')

    results = pd.DataFrame({
        'optimizer_gain': optimizer_gain,
        'dither_amplitude': dither_amplitude,
        'dither_frequency': dither_frequency,
        'converged': trial['converged'],
        'convergence_time': trial['convergence_time'],
    })
    sweeps.write_csv(results, output)
    print(f"converged: {results['converged'].mean():.4f}")


if __name__ == '__main__':
    main()
