"""
Crossed sweep: every ESC parameter set on every plant (PLAN.md, phase 2).

The earlier sweeps vary either the ESC set (one fixed plant per file) or the plant (one fixed ESC set per file).
Here every ESC set runs on every plant, so that what the plant decides (how much there is to gain over r = 0.5)
can be separated from what the ESC decides (how much of it the controller loses).

ESC sets (OTO-crossed-sets.csv)
  set 0-4      the five sets chosen in OTO-ESC_fix.ipynb (column `chosen` has their names)
  set 5-2004   2,000 quasi-random sets: Halton sequence (bases 2, 3, 5; points 1 to 2000) with
               k log-uniform in [1e-3, 5], a uniform in [0.005, 0.6], f uniform in [0.5, 10] Hz

Plants (OTO-crossed-plants.csv): 600 in seven families
  static     41  r_ideal constant: 0.400 to 0.600 in steps of 0.005
  exp        72  r_ideal_0 exp(lambda t) from r_start to r_end in 100 s; both on 0.42, 0.44, ..., 0.58, r_start != r_end
  timescale  30  10 plants of the first two families with both confinement times x0.5, x2 and x3
  linear     30  r_ideal_0 in {0.44, 0.47, 0.50, 0.53, 0.56}, linear change of -0.08 ... +0.08 over the 100 s
  step       36  r_ideal_0 in {0.46, 0.50, 0.54}, step of -0.06, -0.03, +0.03 or +0.06 at t = 20, 50 or 80 s
  sine       27  r_ideal_0 in {0.46, 0.50, 0.54}, plus a sine of amplitude 0.01, 0.03 or 0.06 and period 10, 30 or 100 s
  random    364  as in OTO-ESC_fix: r_ideal_0 uniform in [0.45, 0.55], lambda uniform in [-0.002, 0.002] 1/s
                 (MATLAB's default random stream, seed 0)
  Columns r_ideal_end, r_ideal_mean and offset_rms (root mean square of r_ideal - 0.5 over the run) describe each
  plant; drift_class is static, away (from 0.5), towards, through (crosses 0.5) or oscillating (sine).

Starts and blocks (one CSV file per block)
  static, exp1, exp2, timescale, linear, step, sine, random1 ... random6
           every plant once; the plasma is already running at r = 0.5 (full density, steady state) and r_hat_0 = 0.5
  from0.3, from0.7
           30 plants (column off_start): the plasma runs at r = 0.3 or 0.7 and r_hat starts there
  dt0.002  time-step check: 205 sets (the chosen five and the first 200 quasi-random sets, which cover the whole
           parameter box) on 50 plants
           (column dt_check), steady start at 0.5, dt = 0.002 s instead of 0.01 s

Output (data/OTO-crossed/)
  OTO-crossed-sets.csv, OTO-crossed-plants.csv
  OTO-crossed-references.csv   block, plant, energy_const (r fixed at 0.5), energy_ideal (r = r_ideal(t)),
                               both from the same start and with the same time step as the block
  OTO-crossed-<block>.csv      one row per ESC set and plant: set, plant, energy_gain (= energy_ESC - energy_const),
                               converged, convergence_time, settling_time_0.01, settling_time_0.02, tracking_error,
                               tracking_error_late, r_hat_final (definitions as in Tools/esc_sim.py)
  energy_ESC = energy_const + energy_gain; shortfall from the best possible = energy_ideal - energy_ESC.

Usage
  python OTO_ESC_crossed.py --parallel 8        everything, 8 blocks at a time (about 25 min on 16 cores)
  python OTO_ESC_crossed.py --tables            only the sets, plants and references tables
  python OTO_ESC_crossed.py --block static      one block
  python OTO_ESC_crossed.py --block exp1 --sets 0:100 --plants 0:10 --folder test     a small part of a block
  python OTO_ESC_crossed.py                     everything, one block after the other (about 2 hours)
The MATLAB version (OTO_ESC_crossed.m) makes the same tables and blocks, with file names ending in -matlab.
"""
import argparse
import io
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / 'Tools' / 'esc_sim.py').exists()) / 'Tools'))
import esc_sim as sim          # noqa: E402  (the simulation, checked against the MATLAB data sets)
import esc_sweeps as sweeps    # noqa: E402  (random numbers as in MATLAB)
import esc_paths as paths      # noqa: E402  (where the data folder is)

# ---- Settings -------------------------------------------------------------------------------------------
tend = 100.0                    # run length [s]
dt = 0.01                       # time step [s] (the dt0.002 block uses dt_check)
dt_check = 0.002
n_quasi_random = 2000           # quasi-random ESC sets
n_dt_sets = 200                 # quasi-random sets in the dt0.002 block (the first ones of the Halton sequence)
k_range = (1e-3, 5.0)           # optimizer gain, log-uniform
a_range = (0.005, 0.6)          # dither amplitude
f_range = (0.5, 10.0)           # dither frequency [Hz]
chosen_sets = [                 # (name, k, a, f), from OTO-ESC_fix.ipynb
    ('reference', 1, 0.2, 6),
    ('fastest', 0.255, 0.0517, 8.41),
    ('fastest a>=0.15', 0.265, 0.192, 9.09),
    ('fastest f<=3', 0.0982, 0.0556, 2.97),
    ('best energy a>=0.1', 1.6, 0.11, 9.91),
]
n_random_plants = 364
random_r_ideal_0_range = (0.45, 0.55)
random_lambda_range = (-0.002, 0.002)   # [1/s]
random_seed = 0                 # 0 = the random numbers of a freshly started MATLAB
off_starts = (0.3, 0.7)
chunk = 10000                   # runs simulated at once (memory)

SHAPE_NAMES = ['exp', 'linear', 'step', 'sine']
# plants of the off-0.5 starts and of the time-step check, in thousandths of r (exact in both languages)
OFF_START_STATIC = [420, 460, 500, 540, 580]
EXP_SUBSET = [(460, 540), (540, 460), (480, 420), (520, 580), (460, 500),
              (420, 580), (580, 420), (500, 560), (500, 440), (440, 480)]
DT_STATIC = [400, 450, 475, 500, 525, 550, 600]
TIMESCALE_STATIC = [450, 475, 500, 525, 550]
TIMESCALE_EXP = [(460, 540), (540, 460), (480, 420), (520, 580), (460, 500)]
TIMESCALES = [0.5, 2.0, 3.0]

ROW_COLUMNS = ['set', 'plant', 'energy_gain', 'converged', 'convergence_time', 'settling_time_0.01',
               'settling_time_0.02', 'tracking_error', 'tracking_error_late', 'r_hat_final']
ROW_FORMAT = ['%d', '%d', '%.9g', '%d', '%.6g', '%.6g', '%.6g', '%.6g', '%.6g', '%.9g']


# ---- ESC sets ---------------------------------------------------------------------------------------------
def halton(n, base):
    """Points 1..n of the van der Corput sequence in `base` (one coordinate of the Halton sequence)."""
    i = np.arange(1, n + 1, dtype=float)
    scale = np.ones(n)
    value = np.zeros(n)
    while np.any(i > 0):
        scale = scale / base
        value = value + scale * np.mod(i, base)
        i = np.floor(i / base)
    return value


def esc_sets():
    """Table of all ESC sets: the chosen ones first, then the quasi-random ones."""
    u_k, u_a, u_f = halton(n_quasi_random, 2), halton(n_quasi_random, 3), halton(n_quasi_random, 5)
    k = np.concatenate([[s[1] for s in chosen_sets], sweeps.log_uniform(k_range, u_k)])
    a = np.concatenate([[s[2] for s in chosen_sets], sweeps.uniform(a_range, u_a)])
    f = np.concatenate([[s[3] for s in chosen_sets], sweeps.uniform(f_range, u_f)])
    names = [s[0] for s in chosen_sets] + [''] * n_quasi_random
    return pd.DataFrame({'set': np.arange(k.size), 'optimizer_gain': k, 'dither_amplitude': a,
                         'dither_frequency': f, 'chosen': names})


# ---- Plants ----------------------------------------------------------------------------------------------
def plants():
    """Table of all plants, with the plant parameters for esc_sim and descriptive columns."""
    rows = []      # family, r_ideal_0, lambda, shape, size, time, tau_scale, r_start (1/1000), r_end (1/1000)

    def add(family, r0, lam=0.0, shape=0, size=0.0, t_drift=tend, scale=1.0, start=-1, end=-1):
        rows.append((family, r0, lam, shape, size, t_drift, scale, start, end))

    for j in range(41):
        add('static', (400 + 5 * j) / 1000, start=400 + 5 * j, end=400 + 5 * j)
    for s in range(9):
        for e in range(9):
            if s != e:
                r_start, r_end = 420 + 20 * s, 420 + 20 * e
                add('exp', r_start / 1000, np.log((r_end / 1000) / (r_start / 1000)) / tend, start=r_start, end=r_end)
    for scale in TIMESCALES:
        for r in TIMESCALE_STATIC:
            add('timescale', r / 1000, scale=scale, start=r, end=r)
        for r_start, r_end in TIMESCALE_EXP:
            add('timescale', r_start / 1000, np.log((r_end / 1000) / (r_start / 1000)) / tend, scale=scale,
                start=r_start, end=r_end)
    for r in [440, 470, 500, 530, 560]:
        for d in [-80, -50, -20, 20, 50, 80]:
            add('linear', r / 1000, shape=1, size=d / 1000, t_drift=tend)
    for r in [460, 500, 540]:
        for d in [-60, -30, 30, 60]:
            for t_step in [20, 50, 80]:
                add('step', r / 1000, shape=2, size=d / 1000, t_drift=t_step)
    for r in [460, 500, 540]:
        for amplitude in [10, 30, 60]:
            for period in [10, 30, 100]:
                add('sine', r / 1000, shape=3, size=amplitude / 1000, t_drift=period)
    u = sweeps.draw(sweeps.matlab_rng(random_seed, 0), n_random_plants, ['r_ideal_0', 'lambda_r_ideal'])
    for r0, lam in zip(sweeps.uniform(random_r_ideal_0_range, u['r_ideal_0']),
                       sweeps.uniform(random_lambda_range, u['lambda_r_ideal'])):
        add('random', r0, lam)

    table = pd.DataFrame(rows, columns=['family', 'r_ideal_0', 'lambda_r_ideal', 'shape', 'drift_size',
                                        'drift_time', 'tau_scale', 'start_milli', 'end_milli'])
    table.insert(0, 'plant', np.arange(len(table)))
    table['drift_shape'] = [SHAPE_NAMES[s] for s in table['shape']]

    # r_ideal over the run, sampled every dt
    path = r_ideal_path(np.arange(int(round(tend / dt)) + 1) * dt, table)
    table['r_ideal_end'] = path[-1]
    table['r_ideal_mean'] = path.mean(axis=0)
    table['offset_rms'] = np.sqrt(((path - 0.5) ** 2).mean(axis=0))
    d0, d1 = table['r_ideal_0'] - 0.5, table['r_ideal_end'] - 0.5
    moving = (table['lambda_r_ideal'] != 0) | (table['drift_size'] != 0)
    table['drift_class'] = np.select(
        [~moving, table['shape'] == 3, d0 * d1 < 0, d1.abs() > d0.abs()],
        ['static', 'oscillating', 'through', 'away'], default='towards')

    # blocks of the steady start (at most 61 plants per block)
    block = np.array(table['family'], dtype=object)
    exp_ids = np.flatnonzero(table['family'] == 'exp')
    block[exp_ids[:36]], block[exp_ids[36:]] = 'exp1', 'exp2'
    random_ids = np.flatnonzero(table['family'] == 'random')
    for j, part in enumerate(split(random_ids, 6)):
        block[part] = f'random{j + 1}'
    table['block'] = block

    table['off_start'] = subset_off_start(table).astype(int)
    table['dt_check'] = subset_dt_check(table).astype(int)
    columns = ['plant', 'family', 'block', 'drift_shape', 'r_ideal_0', 'lambda_r_ideal', 'drift_size', 'drift_time',
               'tau_scale', 'r_ideal_end', 'r_ideal_mean', 'offset_rms', 'drift_class', 'off_start', 'dt_check']
    return table[columns + ['shape', 'start_milli', 'end_milli']]


def r_ideal_path(t, table):
    """r_ideal(t) of every plant (time x plants), the same formula as in esc_sim."""
    t = np.asarray(t, dtype=float)[:, None]
    r0, lam = table['r_ideal_0'].to_numpy(), table['lambda_r_ideal'].to_numpy()
    shape, size, t_drift = table['shape'].to_numpy(), table['drift_size'].to_numpy(), table['drift_time'].to_numpy()
    value = r0 * np.exp(lam * t)
    g = np.where(shape == 1, t / t_drift, np.where(shape == 2, (t >= t_drift).astype(float),
                                                   np.where(shape == 3, np.sin(2 * np.pi * t / t_drift), 0.0)))
    return value + size * g


def split(ids, n_parts):
    """Split into n_parts consecutive pieces; the first ones get one more element (as MATLAB's version)."""
    base, extra = divmod(len(ids), n_parts)
    sizes = [base + (j < extra) for j in range(n_parts)]
    edges = np.cumsum([0] + sizes)
    return [ids[edges[j]:edges[j + 1]] for j in range(n_parts)]


def find(table, family, start, end=None, scale=1.0):
    """Plant id of a static or exponential plant given in thousandths."""
    end = start if end is None else end
    hit = np.flatnonzero((table['family'] == family) & (table['start_milli'] == start) & (table['end_milli'] == end)
                         & (table['tau_scale'] == scale))
    assert hit.size == 1, (family, start, end, scale)
    return hit[0]


def evenly(ids, m):
    """m elements spread evenly over ids, first and last included."""
    n = len(ids)
    return [ids[(j * (n - 1)) // (m - 1)] for j in range(m)]


def subset_off_start(table):
    ids = [find(table, 'static', r) for r in OFF_START_STATIC]
    ids += [find(table, 'timescale', r, scale=s) for s in TIMESCALES for r in TIMESCALE_STATIC]
    ids += [find(table, 'exp', r_start, r_end) for r_start, r_end in EXP_SUBSET]
    mask = np.zeros(len(table), dtype=bool); mask[ids] = True
    return mask


def subset_dt_check(table):
    ids = [find(table, 'static', r) for r in DT_STATIC]
    ids += [find(table, 'exp', r_start, r_end) for r_start, r_end in EXP_SUBSET[:8]]
    ids += [find(table, 'timescale', r, scale=s) for s in TIMESCALES for r in (450, 550)]
    for family, m in [('linear', 6), ('step', 6), ('sine', 6), ('random', 11)]:
        ids += evenly(np.flatnonzero(table['family'] == family), m)
    mask = np.zeros(len(table), dtype=bool); mask[ids] = True
    return mask


# ---- Blocks ------------------------------------------------------------------------------------------------
def blocks(table, sets):
    """{block name: (plant ids, set ids, start ratio, time step)} in the order of the files."""
    out = {}
    all_sets = sets['set'].to_numpy()
    for name in ['static', 'exp1', 'exp2', 'timescale', 'linear', 'step', 'sine'] + [f'random{j}' for j in range(1, 7)]:
        out[name] = (np.flatnonzero(table['block'] == name), all_sets, 0.5, dt)
    for start in off_starts:
        out[f'from{start:g}'] = (np.flatnonzero(table['off_start'] == 1), all_sets, start, dt)
    # the first points of a Halton sequence are spread evenly; every tenth point would not be (10 is a multiple of the bases)
    dt_sets = np.concatenate([np.arange(len(chosen_sets)), len(chosen_sets) + np.arange(n_dt_sets)])
    out['dt0.002'] = (np.flatnonzero(table['dt_check'] == 1), dt_sets, 0.5, dt_check)
    return out


def plant_kwargs(table, ids):
    """esc_sim keyword arguments of these plants (one entry per plant)."""
    t = table.iloc[ids]
    return dict(r_ideal_0=t['r_ideal_0'].to_numpy(), lambda_r_ideal=t['lambda_r_ideal'].to_numpy(),
                drift_shape=t['shape'].to_numpy(float), drift_size=t['drift_size'].to_numpy(),
                drift_time=t['drift_time'].to_numpy(), tau_scale=t['tau_scale'].to_numpy())


def references(table, ids, start, step):
    """energy at r fixed at 0.5 and at r = r_ideal(t), from the given start (one entry per plant)."""
    kw = plant_kwargs(table, ids)
    const = sim.simulate(0.0, 0.0, 1.0, use_esc=False, fixed_ratio=0.5, steady_start=start, dt=step, tend=tend, **kw)
    ideal = sim.simulate(0.0, 0.0, 1.0, use_esc=False, fixed_ratio='ideal', steady_start=start, dt=step, tend=tend, **kw)
    return const['energy'], ideal['energy']


def run_block(table, sets, plant_ids, set_ids, start, step, progress=''):
    """All sets on all plants of one block; rows ordered plant by plant, sets inside."""
    n_p, n_s = len(plant_ids), len(set_ids)
    s = sets.iloc[set_ids]
    k = np.tile(s['optimizer_gain'].to_numpy(), n_p)
    a = np.tile(s['dither_amplitude'].to_numpy(), n_p)
    f = np.tile(s['dither_frequency'].to_numpy(), n_p)
    kw = {key: np.repeat(val, n_s) for key, val in plant_kwargs(table, plant_ids).items()}
    out = sim.simulate_in_chunks(k, a, f, r_hat_0=start, steady_start=start, track=True, dt=step, tend=tend,
                                 chunk=chunk, progress=progress, **kw)
    energy_const, _ = references(table, plant_ids, start, step)
    return pd.DataFrame({
        'set': np.tile(np.asarray(set_ids), n_p), 'plant': np.repeat(np.asarray(plant_ids), n_s),
        'energy_gain': out['energy'] - np.repeat(energy_const, n_s),
        'converged': out['converged'].astype(int), 'convergence_time': out['convergence_time'],
        'settling_time_0.01': out['settling_time_0.01'], 'settling_time_0.02': out['settling_time_0.02'],
        'tracking_error': out['tracking_error'], 'tracking_error_late': out['tracking_error_late'],
        'r_hat_final': out['r_hat_final']})


# ---- Files -----------------------------------------------------------------------------------------------------
def write_rows(rows, path):
    buffer = io.StringIO()
    np.savetxt(buffer, rows[ROW_COLUMNS].to_numpy(float), fmt=ROW_FORMAT, delimiter=',',
               header=','.join(ROW_COLUMNS), comments='')
    path.write_text(buffer.getvalue().replace('nan', 'NaN'), encoding='utf-8', newline='\n')
    print(f'{len(rows)} rows written to {path}', flush=True)


def write_table(table, path):
    table.to_csv(path, index=False, float_format='%.15g', na_rep='NaN', lineterminator='\n')
    print(f'{len(table)} rows written to {path}', flush=True)


def checked(path, overwrite):
    if path.exists() and not overwrite:
        raise SystemExit(f'{path} exists already. Choose another --folder or add --overwrite.')
    return path


def parse_slice(text):
    if text is None:
        return slice(None)
    start, stop = text.split(':')
    return slice(int(start) if start else None, int(stop) if stop else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--tables', action='store_true', help='only write the sets, plants and references tables')
    parser.add_argument('--block', help='only this block (see the list above)')
    parser.add_argument('--sets', help='only these sets of the block, as positions start:stop')
    parser.add_argument('--plants', help='only these plants of the block, as positions start:stop')
    parser.add_argument('--parallel', type=int, default=0, help='run the blocks in this many processes at once')
    parser.add_argument('--folder', help='folder for the CSV files (default data/OTO-crossed)')
    parser.add_argument('--overwrite', action='store_true', help='replace existing files')
    args = parser.parse_args()
    folder = Path(args.folder) if args.folder else paths.data_folder('OTO-crossed')
    folder.mkdir(parents=True, exist_ok=True)

    sets, table = esc_sets(), plants()
    block_list = blocks(table, sets)

    if args.block:
        if args.block not in block_list:
            raise SystemExit(f'unknown block {args.block}; choose from {", ".join(block_list)}')
        plant_ids, set_ids, start, step = block_list[args.block]
        plant_ids, set_ids = plant_ids[parse_slice(args.plants)], set_ids[parse_slice(args.sets)]
        suffix = ''.join(f'-{name}{text.replace(":", "-")}' for name, text in [('sets', args.sets), ('plants', args.plants)] if text)
        path = checked(folder / f'OTO-crossed-{args.block}{suffix}.csv', args.overwrite)
        t0 = time.time()
        rows = run_block(table, sets, plant_ids, set_ids, start, step, progress=args.block)
        write_rows(rows, path)
        print(f'{args.block}: {len(rows)} runs in {time.time() - t0:.0f} s, ESC wins {np.mean(rows["energy_gain"] > 0):.3f}, '
              f'converged {rows["converged"].mean():.3f}')
        return

    # tables (sets, plants, references of every block)
    paths_out = [checked(folder / f'OTO-crossed-{name}.csv', args.overwrite) for name in ('sets', 'plants', 'references')]
    write_table(sets, paths_out[0])
    write_table(table.drop(columns=['shape', 'start_milli', 'end_milli']), paths_out[1])
    refs = []
    for name, (plant_ids, _, start, step) in block_list.items():
        const, ideal = references(table, plant_ids, start, step)
        refs.append(pd.DataFrame({'block': name, 'plant': plant_ids, 'energy_const': const, 'energy_ideal': ideal}))
    write_table(pd.concat(refs, ignore_index=True), paths_out[2])
    if args.tables:
        return

    names = list(block_list)
    extra = (['--folder', str(folder)] if args.folder else []) + (['--overwrite'] if args.overwrite else [])
    if args.parallel > 1:
        running, t0 = {}, time.time()
        while names or running:
            while names and len(running) < args.parallel:
                name = names.pop(0)
                running[name] = subprocess.Popen([sys.executable, __file__, '--block', name] + extra,
                                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for name, proc in list(running.items()):
                if proc.poll() is not None:
                    lines = proc.stdout.read().strip().splitlines()
                    print(f'[{time.time() - t0:5.0f} s] {name}: ' + (lines[-1] if lines else '') +
                          ('' if proc.returncode == 0 else f'  (FAILED, exit code {proc.returncode})'), flush=True)
                    del running[name]
            time.sleep(2)
    else:
        for name in names:
            subprocess.run([sys.executable, __file__, '--block', name] + extra, check=True)


if __name__ == '__main__':
    main()
