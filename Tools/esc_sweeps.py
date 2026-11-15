"""
Helpers shared by the Python versions of the MATLAB data-generating scripts
(STO_ESC_constdecay.py, STO_ESC_randdecay.py, OTO_ESC_rand_Plant_rand.py,
OTO_ESC_rand_Plant_fix.py, OTO_ESC_fix_Plant_rand.py).

  matlab_rng()     random numbers identical to MATLAB's rand
  draw()           the rand() calls of one MATLAB trial, for all trials at once
  uniform(), log_uniform()   turn those numbers into parameter values, as the MATLAB scripts do
  arguments()      command-line options common to all scripts
  write_csv()      a CSV file formatted like MATLAB's writetable

The simulation itself is in esc_sim.py.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

MATLAB_DEFAULT_SEED = 5489   # Mersenne-Twister seed behind MATLAB's rng('default') and rng(0)


def matlab_rng(seed=0, skip=0):
    """Random generator that returns the same uniform numbers as rand() in MATLAB.

    MATLAB's default generator is the Mersenne Twister, which NumPy's RandomState also uses.
    seed = 0 is the stream of a freshly started MATLAB (rng('default')); this was checked against
    OTO-ESC-200k.csv, whose parameters are reproduced digit for digit. Other seeds are expected to
    match rng(seed) in MATLAB, but that was not checked.

    skip: number of random numbers to throw away first. A MATLAB session that has already run other
    sweeps continues in the same stream; with the right skip a data set made that way is reproduced
    (the values for the stored data sets are listed in the README).
    """
    rng = np.random.RandomState(MATLAB_DEFAULT_SEED if seed == 0 else seed)
    done = 0
    while done < skip:                      # in blocks, to keep the memory use small
        block = min(skip - done, 1_000_000)
        rng.rand(block)
        done += block
    return rng


def draw(rng, n_trials, names):
    """Uniform random numbers in [0, 1) for all trials: {name: array with one number per trial}.

    `names` lists the rand() calls of ONE trial in the order in which the MATLAB loop makes them.
    The numbers are taken from the stream trial by trial, so every trial gets the same numbers as
    in MATLAB.
    """
    u = rng.rand(n_trials, len(names))
    return {name: u[:, column] for column, name in enumerate(names)}


def uniform(value_range, u):
    """MATLAB: value_range(1) + diff(value_range) * rand()"""
    low, high = value_range
    return low + (high - low) * u


def log_uniform(value_range, u):
    """MATLAB: log_range = log10(value_range);  10^(log_range(1) + diff(log_range) * rand())"""
    low, high = np.log10(value_range)
    return 10.0 ** (low + (high - low) * u)


def count_label(n):
    """200000 -> '200k', 500 -> '500' (used in the default file names)."""
    return f'{n // 1000}k' if n % 1000 == 0 else str(n)


def arguments(description, combinations, seed, extra=()):
    """Read the command line. The defaults are the settings at the top of the calling script.

    extra: additional options as (name, default, help) tuples, e.g. ('--r-ideal-0', 0.5, '...').
    """
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--combinations', type=int, default=combinations, help='number of random sets to test')
    parser.add_argument('--seed', type=int, default=seed, help='random seed (0 = MATLAB default stream)')
    parser.add_argument('--skip', type=int, default=0,
                        help='random numbers to skip first (to continue where an earlier MATLAB sweep stopped)')
    parser.add_argument('--output', default=None, help='CSV file to write (default: see the script)')
    parser.add_argument('--overwrite', action='store_true', help='replace the output file if it exists')
    for name, default, text in extra:
        parser.add_argument(name, type=float, default=default, help=text)
    return parser.parse_args()


def output_path(folder, default_name, args):
    """Full path of the CSV file. Stops if the file exists and --overwrite was not given."""
    path = Path(args.output) if args.output else Path(folder) / default_name
    if path.exists() and not args.overwrite:
        raise SystemExit(f'{path} exists already. Choose another --output or add --overwrite.')
    return path


def write_csv(results, path):
    """Write the table like MATLAB's writetable: 15 significant digits, NaN, true/false as 1/0."""
    results = results.copy()
    for column in results.columns:
        if results[column].dtype == bool:
            results[column] = results[column].astype(int)
    results.to_csv(path, index=False, na_rep='NaN', float_format='%.15g')
    print(f'{len(results)} rows written to {path}')
