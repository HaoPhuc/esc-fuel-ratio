"""
Paired fixed-plant sweep: the SAME random ESC parameter sets on every fixed plant.

Differences from OTO_ESC_rand_Plant_fix.py (which reproduces the MATLAB sweeps):
  * every plant gets the same ESC parameter sets, so one set can be followed across plants;
  * the sets are drawn only where ESC is useful: k 0.02-5 (log-uniform), a 0-0.6, f 1.5-10 Hz;
  * every run starts from a plasma that is already running (full density, steady state with the
    fuel ratio at 0.5) instead of the 25 % deuterium-rich start, which does not occur in practice;
  * extra columns:
        energy_ideal         energy when the ratio follows r_ideal(t) exactly (best possible)
        tracking_error       mean distance between the ratio the plasma receives (1 s average)
                             and r_ideal, over the run
        tracking_error_late  the same over the second half of the run
        settling_time_0.01   time after which that distance stays below 0.01 (NaN: never)
        settling_time_0.02   the same for 0.02
    converged and convergence_time (5 % band on r_hat) are kept for comparison.

Output: one file per plant, OTO-paired-<r_ideal_0>_<lambda>-<runs>.csv, rows in the same order in
every file (row i is the same ESC set everywhere).

Usage
    python OTO_ESC_paired_Plant_fix.py                      all plants (8 x 40,000 runs)
    python OTO_ESC_paired_Plant_fix.py --plant 2            only plant number 2 of the list below
    python OTO_ESC_paired_Plant_fix.py --combinations 1000 --folder test
Start several "--plant" runs at the same time to use more cores.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402
import esc_sweeps as sweeps    # noqa: E402

# ---- Batch sweep settings ----------------------------------------------------
combinations = 40_000           # ESC parameter sets (each is run on every plant)
seed = 0                        # same seed for every plant -> same sets

# ---- Plants: (r_ideal_0, lambda_r_ideal [1/s]);  r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t)
plants = [(0.5, 0.001), (0.5, -0.001), (0.55, 0.002), (0.45, -0.002),
          (0.525, 0.0), (0.475, 0.0), (0.5375, -0.0015), (0.4625, 0.0015)]

# ---- Simulation settings ------------------------------------------------------
tend = 100                      # [s]
dt = 0.01                       # [s]
r_hat_0 = 0.5                   # ESC starting fuel ratio
const_ratio = 0.5               # fixed fuel ratio without ESC
start_ratio = 0.5               # the plasma has been running at this ratio before t = 0
settle_tolerances = (0.01, 0.02)

# ---- ESC parameter ranges (the region where ESC is useful) ---------------------
optimizer_gain_range = (0.02, 5)
dither_amplitude_range = (0, 0.6)
dither_frequency_range = (1.5, 10)


def plant_tag(r_ideal_0, lambda_r_ideal):
    return f'{r_ideal_0:g}' + (f'_{lambda_r_ideal:g}' if lambda_r_ideal != 0 else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--combinations', type=int, default=combinations)
    parser.add_argument('--seed', type=int, default=seed, help='random seed (0 = MATLAB default stream)')
    parser.add_argument('--plant', type=int, action='append', help='index in the plant list (default: all)')
    parser.add_argument('--folder', default=str(HERE), help='folder for the CSV files')
    parser.add_argument('--overwrite', action='store_true', help='replace existing files')
    args = parser.parse_args()
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)

    # ESC parameters (randomized); the same numbers for every plant
    u = sweeps.draw(sweeps.matlab_rng(args.seed), args.combinations,
                    ['dither_amplitude', 'dither_frequency', 'optimizer_gain'])
    dither_amplitude = sweeps.uniform(dither_amplitude_range, u['dither_amplitude'])
    dither_frequency = sweeps.uniform(dither_frequency_range, u['dither_frequency'])
    optimizer_gain = sweeps.log_uniform(optimizer_gain_range, u['optimizer_gain'])

    for index in (args.plant if args.plant else range(len(plants))):
        r_ideal_0, lambda_r_ideal = plants[index]
        tag = plant_tag(r_ideal_0, lambda_r_ideal)
        output = folder / f'OTO-paired-{tag}-{sweeps.count_label(args.combinations)}.csv'
        if output.exists() and not args.overwrite:
            raise SystemExit(f'{output} exists already. Add --overwrite to replace it.')
        plant = dict(r_ideal_0=r_ideal_0, lambda_r_ideal=lambda_r_ideal, steady_start=start_ratio, dt=dt, tend=tend)

        # references on this plant: ratio fixed at 0.5, and ratio following r_ideal(t) exactly
        energy_const = sim.simulate(1, 0.1, 1, use_esc=False, fixed_ratio=const_ratio, **plant)['energy'][0]
        energy_ideal = sim.simulate(1, 0.1, 1, use_esc=False, fixed_ratio='ideal', **plant)['energy'][0]

        esc = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency, r_hat_0=r_hat_0,
                                     track=True, settle_tolerances=settle_tolerances,
                                     progress=f'plant {tag}', **plant)
        results = pd.DataFrame({
            'optimizer_gain': optimizer_gain,
            'dither_amplitude': dither_amplitude,
            'dither_frequency': dither_frequency,
            'r_ideal_0': r_ideal_0,
            'lambda_r_ideal': lambda_r_ideal,
            'energy_ESC': esc['energy'],
            'energy_const': energy_const,
            'energy_ideal': energy_ideal,
            'energy_max': 0.25 * sim.N_REF ** 2 * tend,
            'choose_ESC': (esc['energy'] > energy_const).astype(int),
            'tracking_error': esc['tracking_error'],
            'tracking_error_late': esc['tracking_error_late'],
            **{f'settling_time_{tol:g}': esc[f'settling_time_{tol:g}'] for tol in settle_tolerances},
            'converged': esc['converged'],
            'convergence_time': esc['convergence_time'],
        })
        sweeps.write_csv(results, output)


if __name__ == '__main__':
    main()
