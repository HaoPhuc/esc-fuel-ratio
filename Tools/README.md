# Tools

Code shared by the notebooks and the data-generating (sweep) scripts. The simulation exists in Python and in MATLAB;
both follow the same loop step for step and give the same numbers to rounding.

## Python

| File | What it is |
|---|---|
| `esc_sim.py` | The simulation. `simulate()` runs many ESC runs at once (one array element per run); `simulate_in_chunks()` does the same in batches to limit memory. It is a port of the loop in the MATLAB scripts and has the options used by the newer sweeps (steady start, tracking error, settling time, dither phase, mirrored plant, requested-to-received ratio map, plant time scale `tau_scale`, drift shapes `drift_shape` = exp, linear, step or sine). |
| `esc_sweeps.py` | Helpers for the Python sweep scripts: `matlab_rng()` (the same random numbers as MATLAB's `rand`), `draw()` (the random numbers of each trial in MATLAB's order), `uniform()`, `log_uniform()`, the common command-line options (`arguments()`, `output_path()`), `write_csv()` and `count_label()`. |
| `esc_tools.py` | Everything the notebooks share: the plot style (`apply_style()`, colours, axis labels), the model constants, the averaged-ESC formulas (`c_factor()`, `lam_avg()`, `dither_loss()`, `add_esc_quantities()`, `well_tuned()`), the plotting helpers (`outcome_bar()`, `time_hist()`, `scatter_grid()`, `pair_plot()`, `corr_heatmap()`, `convergence_vs_rate()`, `energy_vs_tuning()`, `plant_map()`, `plant_grid()`, `gain_vs_plant()`, `gain_boxplot()`, `gain_ecdf()`, `loss_curves()`, `scatter3d()`) and the smoothed heat maps (`bins_for()`, `binned_map()`). |
| `esc_paths.py` | Where the data are: `ROOT` (the repository), `DATA` (`data/`), `data_folder(name)` (a subfolder of `data/`, made if it does not exist) and `data_file(name)` (a data file found by its name anywhere under `data/`). `esc_tools.read_data(name)` reads such a file with pandas. |
| `esc_ml.py` | PyTorch helpers for the classifiers in the notebooks: `split_data()` (60/20/20), `make_model()`, `train_classifier()`, `predict()`, `accuracy()`, `majority_baseline()`, `report()`, `summary_table()`, `error_table()`. |
| `validate_esc_sim.py` | Checks `esc_sim.py` against the data sets made in MATLAB. Run from the repository root: `python Tools/validate_esc_sim.py`. |

The notebooks find this folder themselves (they look for `Tools/esc_tools.py` in the current folder and its parents).
The Python sweep scripts in `generators/` do the same.

## MATLAB

| File | What it is |
|---|---|
| `esc_sim.m` | MATLAB version of `esc_sim.py`: `out = esc_sim(k, a, f, 'Name', value, ...)`. Same model, same options (as name-value pairs, e.g. `'RIdeal0'`, `'SteadyStart'`, `'Track'`), many runs at once. Type `help esc_sim` for the full list. |
| `esc_rng.m` | `esc_rng(seed, skip)`: starts MATLAB's random stream as the sweeps do (seed 0 = `rng('default')`) and throws away `skip` numbers first. |
| `esc_draw.m` | `u = esc_draw(n_trials, n_calls)`: the random numbers of all trials, one row per trial, in the order of a trial-by-trial loop (the same numbers as `esc_sweeps.draw()` in Python). |
| `esc_write_csv.m` | `esc_write_csv(file, names, columns)`: writes the results with 15 significant digits, as the Python scripts do. |
| `esc_paths.m` | MATLAB version of `esc_paths.py`: `esc_paths()` is `data/`, `esc_paths('root')` the repository, `esc_paths('OTO-paired')` a subfolder of `data/` (made if it does not exist), `esc_paths('file', name)` a data file found by its name anywhere under `data/`. |
| `validate_matlab_ports.m` | Re-simulates the first rows of stored data sets (one MATLAB data set and the five data sets first made in Python, below) with `esc_sim.m` and prints the differences. Run it once after changing `esc_sim.m`. |

The MATLAB sweep scripts in `generators/` add this folder to the path themselves (`addpath(fullfile(here, '..', 'Tools'))`).
Needs MATLAB R2020b or newer (`readtable` with `'VariableNamingRule'` in the validation script, local functions
in scripts).

Example:

```matlab
addpath('Tools')
out = esc_sim(1, 0.2, 6, 'RIdeal0', 0.525, 'RHat0', 0.5, 'SteadyStart', 0.5, 'Track', true);
out.energy, out.settling_time      % energy and settling times (tolerances 0.01 and 0.02)
```

## Which script makes which data set

Every sweep can be run in both languages. All scripts are in `generators/` and all data sets in a subfolder of
`data/`. The original MATLAB scripts contain the simulation loop themselves; all other scripts use `esc_sim.py`
or `esc_sim.m`.

| Data set | MATLAB | Python |
|---|---|---|
| `STO-const_decay-200k.csv` | `STO_ESC_constdecay.m` (original) | `STO_ESC_constdecay.py` |
| `STO-random_decay-200k.csv` | `STO_ESC_randdecay.m` (original) | `generate_STO_random_decay.py` (made the stored file), `STO_ESC_randdecay.py` |
| `OTO-ESC-200k.csv`, `OTO-ESC-10k.csv` | `OTO_ESC_rand_Plant_rand.m` (original) | `OTO_ESC_rand_Plant_rand.py` |
| `OTO-Plant_fix-*-100kshots.csv` | `OTO_ESC_rand_Plant_fix.m` (original) | `OTO_ESC_rand_Plant_fix.py` |
| `OTO-ESC_fix-1_0.2_6-100kshots.csv` | `OTO_ESC_fix_Plant_rand.m` (original) | `OTO_ESC_fix_Plant_rand.py` |
| `OTO-paired-*-40k.csv` | `OTO_ESC_paired_Plant_fix.m` | `OTO_ESC_paired_Plant_fix.py` (made the stored files) |
| `OTO-ESC_chosen-*-100k.csv` | `OTO_ESC_chosen_Plant_rand.m` | `OTO_ESC_chosen_Plant_rand.py` (made the stored files) |
| `OTO-losing_region-*.csv` | `OTO_ESC_losing_region.m` | `OTO_ESC_losing_region.py` (made the stored files) |
| `OTO-mirror_symmetry_test.csv` | `mirror_symmetry_test.m` | `mirror_symmetry_test.py` (made the stored file) |
| `OTO-crossed-*.csv` | `OTO_ESC_crossed.m` | `OTO_ESC_crossed.py` (made the stored files) |

- Both languages draw the same random numbers (MATLAB's Mersenne Twister, in the same order), so a script in one
  language reproduces the data set made by the other. The one exception is `generate_STO_random_decay.py`, which
  uses NumPy's own generator: `STO_ESC_randdecay.m` runs the same experiment, but with other random parameter sets.
- To protect the stored files, the Python ports of the original MATLAB scripts write names ending in `-python`, and
  the MATLAB versions of the Python scripts write names ending in `-matlab`.
- The settings (number of runs, plants, ESC sets, output folder) are at the top of every script. By default each
  script writes into its own subfolder of `data/` (`esc_paths`). The Python scripts
  also take them on the command line (`python <script> --help`), except `generate_STO_random_decay.py`, which takes
  the number of runs and the seed as plain arguments.

**Status (24 November 2026):** the MATLAB files `esc_sim.m`, `esc_rng.m`, `esc_draw.m`, `esc_write_csv.m`,
`validate_matlab_ports.m` and the four new MATLAB sweep scripts were written to follow the Python code line by
line, but MATLAB could not be run when they were written. Run `validate_matlab_ports.m` once; every line should end
in `ok`. The same holds for the options added on 25 November 2026 (`'TauScale'`, `'DriftShape'`, `'DriftSize'`,
`'DriftTime'` in `esc_sim.m`) and for `OTO_ESC_crossed.m`; section F of `validate_matlab_ports.m` checks them.
