"""
Why do mirror plants give different results?  A symmetry test.

The model is unchanged when deuterium and tritium are exchanged (r -> 1 - r), provided that
everything else is exchanged too. In the stored sweeps three things are NOT exchanged
between a plant and its mirror twin:

  1. the dither starts upwards in both (r = r_hat + a sin(w t)); the mirror image would start downwards;
  2. the initial densities are deuterium-rich in both (set with r = 0.1); the mirror image would be
     tritium-rich (r = 0.9);
  3. for the drifting plants, r_ideal_0 exp(lambda t) of the twin is not exactly 1 - r_ideal(t) of the plant.

This script simulates plant A of each pair and its twin B with the same ESC parameters
(the first N_RUNS rows of plant A's data set), and repeats B with the dither flipped,
with the initial densities mirrored, and with both. energy_A_mirror is the exact mirror image of A
(all three items exchanged); it equals energy_A up to rounding. A few runs (about 0.2 %) are sensitive
to rounding errors and differ more; their choose_ESC label is still the same.
energy_A_sym and energy_B_sym start both plants from equal D and T densities (r = 0.5), so that the
direction of the dither is the only difference left for the plants without drift.
The const_* columns are the benchmark (fuel ratio fixed at 0.5) for the same plant and initial state.

Output: OTO-mirror_symmetry_test.csv (one row per pair and ESC parameter set).
Run:    python mirror_symmetry_test.py                      all pairs, one after the other (about 30 min)
        python mirror_symmetry_test.py --pairs 0 --output part0.csv
                                                            one pair only; start several of these at the
                                                            same time to use more cores, then join the files
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'Tools'))
import esc_sim as sim  # noqa: E402

N_RUNS = 10000
R_HAT_0 = 0.5            # as in the optimal-to-operate sweeps

# (name A, r_ideal_0, lambda, file tag of A), (name B, r_ideal_0, lambda)
PAIRS = [
    (('0.5 up 0.001', 0.5, 0.001, '0.5_0.001'), ('0.5 down 0.001', 0.5, -0.001)),
    (('0.55 up 0.002', 0.55, 0.002, '0.55_0.002'), ('0.45 down 0.002', 0.45, -0.002)),
    (('0.525', 0.525, 0.0, '0.525'), ('0.475', 0.475, 0.0)),
    (('0.5375 down 0.0015', 0.5375, -0.0015, '0.5375_-0.0015'), ('0.4625 up 0.0015', 0.4625, 0.0015)),
]

# column -> options that differ from the stored sweeps
VARIANTS = {
    'energy_A':        dict(plant='A'),
    'energy_B':        dict(plant='B'),
    'energy_B_flip':   dict(plant='B', dither_phase=np.pi),
    'energy_B_init':   dict(plant='B', initial_ratio=0.9),
    'energy_B_both':   dict(plant='B', dither_phase=np.pi, initial_ratio=0.9),
    'energy_A_mirror': dict(plant='A', mirror_plant=True, dither_phase=np.pi, initial_ratio=0.9),
    'energy_A_sym':    dict(plant='A', initial_ratio=0.5),
    'energy_B_sym':    dict(plant='B', initial_ratio=0.5),
}


def run(pair_index, column, esc):
    """Energies of one variant (one column of the output) for the ESC parameters in `esc`."""
    (name_a, r0_a, lam_a, tag), (name_b, r0_b, lam_b) = PAIRS[pair_index]
    options = dict(VARIANTS[column])
    r0, lam = (r0_a, lam_a) if options.pop('plant') == 'A' else (r0_b, lam_b)
    out = sim.simulate(esc['optimizer_gain'], esc['dither_amplitude'], esc['dither_frequency'],
                       r_ideal_0=r0, lambda_r_ideal=lam, r_hat_0=R_HAT_0, **options)
    return out['energy']


def fixed_ratio_energy(r0, lam, initial_ratio=sim.INITIAL_RATIO):
    """Energy of the same plant with the fuel ratio fixed at 0.5 (the benchmark)."""
    return sim.simulate(1, 0.1, 1, r_ideal_0=r0, lambda_r_ideal=lam, use_esc=False,
                        initial_ratio=initial_ratio)['energy'][0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--pairs', type=int, nargs='*', default=list(range(len(PAIRS))),
                        help='indices of the mirror pairs to simulate (default: all)')
    parser.add_argument('--output', default=str(HERE / 'OTO-mirror_symmetry_test.csv'))
    args = parser.parse_args()

    frames = []
    for i in args.pairs:
        (name_a, r0_a, lam_a, tag), (name_b, r0_b, lam_b) = PAIRS[i]
        df = pd.read_csv(HERE / f'OTO-Plant_fix-{tag}-100kshots.csv',
                         usecols=['optimizer_gain', 'dither_amplitude', 'dither_frequency'], nrows=N_RUNS)
        esc = df.copy()
        df.insert(0, 'plant_B', name_b)
        df.insert(0, 'plant_A', name_a)
        for column in VARIANTS:
            df[column] = run(i, column, esc)
            print(f'{name_a}: {column} done', flush=True)
        # benchmark (r = 0.5) for every case; the dither does not enter, the initial state does
        df['const_A'] = fixed_ratio_energy(r0_a, lam_a)
        df['const_B'] = fixed_ratio_energy(r0_b, lam_b)
        df['const_B_init'] = fixed_ratio_energy(r0_b, lam_b, initial_ratio=0.9)
        df['const_A_sym'] = fixed_ratio_energy(r0_a, lam_a, initial_ratio=0.5)
        df['const_B_sym'] = fixed_ratio_energy(r0_b, lam_b, initial_ratio=0.5)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(args.output, index=False)
    print(out.groupby('plant_A', sort=False).size())
