"""
Chosen ESC sets on random plants (follow-up of the fixed-plant analysis).

Every ESC set below is run on the SAME 100,000 random plants, r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t),
with r_ideal_0 in [0.45, 0.55] and lambda_r_ideal in [-0.002, 0.002] 1/s. The plants are the ones of the MATLAB
data set OTO-ESC_fix-1_0.2_6-100kshots.csv (same random numbers, --skip 1812645), so row i is the same plant there.

Settings as in OTO_ESC_paired_Plant_fix.py (not as in the MATLAB script):
  * every run starts from a plasma that is already running (full density, steady state with the ratio at 0.5);
  * extra columns tracking_error, tracking_error_late, settling_time_0.01, settling_time_0.02
    (from the ratio the plasma receives, see Tools/esc_sim.py).

Output
    OTO-ESC_chosen-references-100k.csv     per plant: energy with the ratio fixed at 0.5 (energy_const) and with
                                           the ratio following r_ideal(t) exactly (energy_ideal)
    OTO-ESC_chosen-<k>_<a>_<f>-100k.csv    one file per ESC set
Rows are in the same order in every file.

Usage
    python OTO_ESC_chosen_Plant_rand.py --references      the two reference runs
    python OTO_ESC_chosen_Plant_rand.py --set 2           ESC set number 2 of the list below
    python OTO_ESC_chosen_Plant_rand.py                   everything, one after the other (a few hours)
    python OTO_ESC_chosen_Plant_rand.py --set 2 --rows 0:25000 --output part.csv    only some of the plants
Start several runs at the same time to use more cores.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402
import esc_sweeps as sweeps    # noqa: E402

# ---- ESC sets: (name, optimizer gain k, dither amplitude a, dither frequency f [Hz]) --------------------
# Picked in OTO-Plant_fix-paired.ipynb among the sets with eta >= 0.9 on all eight plants that settle within
# 0.01 on every plant with a late tracking error below 0.005 (values rounded to 3 significant digits).
esc_sets = [
    ('reference', 1, 0.2, 6),                    # chosen from the 3-D plots in OTO-Plant_fix.ipynb
    ('fastest', 0.255, 0.0517, 8.41),            # shortest worst settling time
    ('fastest, a >= 0.15', 0.265, 0.192, 9.09),  # the same with a dither large enough to see in a noisy signal
    ('fastest, f <= 3 Hz', 0.0982, 0.0556, 2.97),  # the same with a slow dither
    ('best energy, a >= 0.1', 1.6, 0.11, 9.91),  # highest worst-plant energy score with a >= 0.1
]

# ---- Plants (as in OTO_ESC_fix_Plant_rand.m) ----------------------------------
combinations = 100_000
seed = 0
skip = 1_812_645                # where the MATLAB session was when it made OTO-ESC_fix-1_0.2_6-100kshots.csv
r_ideal_0_range = (0.45, 0.55)
lambda_r_ideal_range = (-0.002, 0.002)   # [1/s]

# ---- Simulation settings ------------------------------------------------------
tend = 100                      # [s]
dt = 0.01                       # [s]
r_hat_0 = 0.5                   # ESC starting fuel ratio
const_ratio = 0.5               # fixed fuel ratio without ESC
start_ratio = 0.5               # the plasma has been running at this ratio before t = 0
settle_tolerances = (0.01, 0.02)


def set_tag(k, a, f):
    return f'{k:g}_{a:g}_{f:g}'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--references', action='store_true', help='run the two reference cases')
    parser.add_argument('--set', type=int, action='append', help='index in the list of ESC sets')
    parser.add_argument('--rows', default=None, help='only these plants, for example 0:25000')
    parser.add_argument('--output', default=None, help='CSV file (only with one --set or --references)')
    parser.add_argument('--folder', default=str(HERE), help='folder for the CSV files')
    parser.add_argument('--overwrite', action='store_true', help='replace existing files')
    args = parser.parse_args()
    jobs = (['references'] if args.references else []) + (args.set or [])
    if not jobs:
        jobs = ['references', *range(len(esc_sets))]
    if args.output and len(jobs) > 1:
        raise SystemExit('--output can only be used for one job')

    # Plants (randomized); one MATLAB trial calls rand() in this order
    u = sweeps.draw(sweeps.matlab_rng(seed, skip), combinations, ['r_ideal_0', 'lambda_r_ideal'])
    rows = slice(*(int(x) if x else None for x in args.rows.split(':'))) if args.rows else slice(None)
    r_ideal_0 = sweeps.uniform(r_ideal_0_range, u['r_ideal_0'])[rows]
    lambda_r_ideal = sweeps.uniform(lambda_r_ideal_range, u['lambda_r_ideal'])[rows]
    plant = dict(r_ideal_0=r_ideal_0, lambda_r_ideal=lambda_r_ideal, steady_start=start_ratio, dt=dt, tend=tend)
    label = sweeps.count_label(combinations)

    for job in jobs:
        if job == 'references':
            name = f'OTO-ESC_chosen-references-{label}.csv'
        else:
            name = f'OTO-ESC_chosen-{set_tag(*esc_sets[job][1:])}-{label}.csv'
        output = Path(args.output) if args.output else Path(args.folder) / name
        if output.exists() and not args.overwrite:
            raise SystemExit(f'{output} exists already. Add --overwrite to replace it.')

        if job == 'references':
            const = sim.simulate_in_chunks(1, 0.1, 1, use_esc=False, fixed_ratio=const_ratio, progress='ratio 0.5', **plant)
            ideal = sim.simulate_in_chunks(1, 0.1, 1, use_esc=False, fixed_ratio='ideal', progress='ideal ratio', **plant)
            results = pd.DataFrame({'r_ideal_0': r_ideal_0, 'lambda_r_ideal': lambda_r_ideal,
                                    'energy_const': const['energy'], 'energy_ideal': ideal['energy'],
                                    'energy_max': 0.25 * sim.N_REF ** 2 * tend})
        else:
            set_name, k, a, f = esc_sets[job]
            out = sim.simulate_in_chunks(k, a, f, r_hat_0=r_hat_0, track=True, settle_tolerances=settle_tolerances,
                                         progress=set_name, **plant)
            results = pd.DataFrame({
                'optimizer_gain': k, 'dither_amplitude': a, 'dither_frequency': f,
                'r_ideal_0': r_ideal_0, 'lambda_r_ideal': lambda_r_ideal,
                'energy_ESC': out['energy'],
                'tracking_error': out['tracking_error'],
                'tracking_error_late': out['tracking_error_late'],
                **{f'settling_time_{tol:g}': out[f'settling_time_{tol:g}'] for tol in settle_tolerances},
                'converged': out['converged'],
                'convergence_time': out['convergence_time'],
            })
        sweeps.write_csv(results, output)


if __name__ == '__main__':
    main()
