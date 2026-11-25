"""
Python version of OTO_ESC_rand_Plant_fix.m

Optimal to operate: random ESC parameters on ONE fixed plant, r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t).
The energy with the fuel ratio fixed at 0.5 is the same for every trial and is computed once.
Output columns: optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, energy_ESC,
energy_const, energy_max, choose_ESC, converged, convergence_time.

The simulation is not repeated in this file: it is in Tools/esc_sim.py, which follows the MATLAB loop
step for step and simulates many parameter sets at once. The convergence rule (r_hat within 5 % of the
ideal ratio for 5 s) and the model constants are set there.

Usage
    python OTO_ESC_rand_Plant_fix.py                                        plant set below, 100,000 runs
    python OTO_ESC_rand_Plant_fix.py --r-ideal-0 0.55 --lambda-r-ideal 0.002
    python OTO_ESC_rand_Plant_fix.py --combinations 1000 --output test.csv
The default file name is built from the plant, as for the MATLAB data sets, and ends in "-python"
(for example OTO-Plant_fix-0.55_0.002-100kshots-python.csv), so no MATLAB data set is replaced by accident.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402  (the simulation, checked against the MATLAB data sets)
import esc_sweeps as sweeps    # noqa: E402  (random numbers and file output as in MATLAB)

# ---- Batch sweep settings ----------------------------------------------------
combinations = 100_000          # total random sets to test
seed = 0                        # 0 = the random numbers of a freshly started MATLAB

# ---- Plant parameters (constant for every trial; choose them here or on the command line) ----
r_ideal_0 = 0.4625
lambda_r_ideal = 0.0015         # [1/s]

# ---- Simulation settings ------------------------------------------------------
tend = 100                      # [s]
dt = 0.01                       # [s]
r_hat_0 = 0.5                   # ESC starting fuel ratio
const_ratio = 0.5               # fixed fuel ratio without ESC

# ---- ESC parameter ranges -----------------------------------------------------
optimizer_gain_range = (1e-5, 5)
dither_amplitude_range = (0, 1)
dither_frequency_range = (0, 10)


def main():
    args = sweeps.arguments(__doc__, combinations, seed, extra=[
        ('--r-ideal-0', r_ideal_0, 'ideal fuel ratio at t = 0'),
        ('--lambda-r-ideal', lambda_r_ideal, 'drift rate of the ideal ratio [1/s]')])
    plant = f'{args.r_ideal_0:g}' + (f'_{args.lambda_r_ideal:g}' if args.lambda_r_ideal != 0 else '')
    output = sweeps.output_path(
        HERE, f'OTO-Plant_fix-{plant}-{sweeps.count_label(args.combinations)}shots-python.csv', args)

    # Fixed-ratio energy (the plant is the same in every trial, so compute it once)
    energy_const = sim.simulate(1, 0.1, 1, r_ideal_0=args.r_ideal_0, lambda_r_ideal=args.lambda_r_ideal,
                                use_esc=False, fixed_ratio=const_ratio, dt=dt, tend=tend)['energy'][0]

    # ESC parameters (randomized); one MATLAB trial calls rand() in this order
    u = sweeps.draw(sweeps.matlab_rng(args.seed, args.skip), args.combinations,
                    ['dither_amplitude', 'dither_frequency', 'optimizer_gain'])
    dither_amplitude = sweeps.uniform(dither_amplitude_range, u['dither_amplitude'])
    dither_frequency = sweeps.uniform(dither_frequency_range, u['dither_frequency'])
    optimizer_gain = sweeps.log_uniform(optimizer_gain_range, u['optimizer_gain'])   # randomize the power

    # Run all trials
    esc = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency,
                                 r_ideal_0=args.r_ideal_0, lambda_r_ideal=args.lambda_r_ideal, r_hat_0=r_hat_0,
                                 dt=dt, tend=tend, progress='ESC trials')

    results = pd.DataFrame({
        'optimizer_gain': optimizer_gain,
        'dither_amplitude': dither_amplitude,
        'dither_frequency': dither_frequency,
        'r_ideal_0': args.r_ideal_0,
        'lambda_r_ideal': args.lambda_r_ideal,
        'energy_ESC': esc['energy'],
        'energy_const': energy_const,
        # theoretical maximum: n_D = n_T = n_ref/2 the whole time (same for every case)
        'energy_max': 0.25 * sim.N_REF ** 2 * tend,
        # should we choose ESC? (1 = ESC gives more energy than the fixed ratio)
        'choose_ESC': (esc['energy'] > energy_const).astype(int),
        'converged': esc['converged'],
        'convergence_time': esc['convergence_time'],
    })
    sweeps.write_csv(results, output)
    print(f"choose_ESC: {results['choose_ESC'].mean():.4f}   converged: {results['converged'].mean():.4f}")


if __name__ == '__main__':
    main()
