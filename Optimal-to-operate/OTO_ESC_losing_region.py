"""
Where does ESC lose against r = 0.5? One ESC set on a regular grid of plants near r_ideal = 0.5.

The plants are r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t) on a grid of r_ideal_0 and lambda_r_ideal around
(0.5, 0), where the region in which ESC loses lies (see OTO-ESC_fix.ipynb, Section 8). Four cases:

    steady-T50, steady-T100, steady-T200   runs of 50, 100 and 200 s that start from a plasma already running
                                           at r = 0.5 (as in OTO_ESC_chosen_Plant_rand.py)
    matlab-T100                            runs of 100 s with the start of the MATLAB scripts
                                           (25 % density, deuterium-rich)

For every plant: energy with ESC, with the ratio fixed at 0.5 (energy_const) and with the ratio following
r_ideal(t) exactly (energy_ideal).

Output: OTO-losing_region-<case>.csv, one row per plant.

Usage
    python OTO_ESC_losing_region.py                    all four cases, one after the other (about 10 min)
    python OTO_ESC_losing_region.py --case steady-T200 one case (start several at the same time to use more cores)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402
import esc_sweeps as sweeps    # noqa: E402

# ---- ESC set (the reference set of OTO-ESC_fix.ipynb) ---------------------------
optimizer_gain = 1
dither_amplitude = 0.2
dither_frequency = 6            # [Hz]

# ---- Plant grid ----------------------------------------------------------------
r_ideal_0_grid = np.linspace(0.48, 0.52, 81)          # step 0.0005
lambda_r_ideal_grid = np.linspace(-1e-3, 1e-3, 101)   # step 2e-5 [1/s]

# ---- Cases: name -> (run length [s], start) --------------------------------------
cases = {
    'steady-T50': (50, 'steady'),
    'steady-T100': (100, 'steady'),
    'steady-T200': (200, 'steady'),
    'matlab-T100': (100, 'matlab'),
}

dt = 0.01                       # [s]
r_hat_0 = 0.5                   # ESC starting fuel ratio
const_ratio = 0.5               # fixed fuel ratio without ESC
start_ratio = 0.5               # steady start: the plasma has been running at this ratio before t = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--case', action='append', choices=list(cases), help='case to run (default: all)')
    parser.add_argument('--folder', default=str(HERE), help='folder for the CSV files')
    parser.add_argument('--overwrite', action='store_true', help='replace existing files')
    args = parser.parse_args()

    r0, lam = np.meshgrid(r_ideal_0_grid, lambda_r_ideal_grid, indexing='ij')
    r0, lam = r0.ravel(), lam.ravel()
    for name in (args.case or list(cases)):
        output = Path(args.folder) / f'OTO-losing_region-{name}.csv'
        if output.exists() and not args.overwrite:
            raise SystemExit(f'{output} exists already. Add --overwrite to replace it.')
        tend, start = cases[name]
        plant = dict(r_ideal_0=r0, lambda_r_ideal=lam, dt=dt, tend=tend)
        if start == 'steady':
            plant['steady_start'] = start_ratio
        const = sim.simulate_in_chunks(1, 0.1, 1, use_esc=False, fixed_ratio=const_ratio, progress=f'{name}: ratio 0.5', **plant)
        ideal = sim.simulate_in_chunks(1, 0.1, 1, use_esc=False, fixed_ratio='ideal', progress=f'{name}: ideal ratio', **plant)
        esc = sim.simulate_in_chunks(optimizer_gain, dither_amplitude, dither_frequency, r_hat_0=r_hat_0,
                                     progress=f'{name}: ESC', **plant)
        results = pd.DataFrame({
            'case': name, 'tend': tend, 'start': start,
            'optimizer_gain': optimizer_gain, 'dither_amplitude': dither_amplitude, 'dither_frequency': dither_frequency,
            'r_ideal_0': r0, 'lambda_r_ideal': lam,
            'energy_ESC': esc['energy'], 'energy_const': const['energy'], 'energy_ideal': ideal['energy'],
        })
        sweeps.write_csv(results, output)


if __name__ == '__main__':
    main()
