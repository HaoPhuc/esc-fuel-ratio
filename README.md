# Extremum Seeking Control for D–T Fuel Ratio Optimization

This repository contains the documentation and code of my research project "Extremum Seeking Control for D–T
Fuel Ratio Optimization", under the supervision of Juan Javier Palacios Roman.

Fusion power scales with the product of the deuterium and tritium densities, $n_D n_T$. Extremum seeking control
(ESC) tunes the tritium fraction $r$ of the fuelling online, using only a measurement proportional to $n_D n_T$,
so that this product is maximised without knowing the particle loss rates.

## Goals of the current phase

The current phase answers two questions in the noise-free first-order model. Both use the crossed data set
(`data/OTO-crossed/`): every one of 2,005 ESC settings was run on every one of 600 test plants. A summary for the
supervisor is in [`SUPERVISOR_SUMMARY.md`](SUPERVISOR_SUMMARY.md).

1. **Is ESC better than a fixed fuel ratio r = 0.5?** It should win more often, and its wins should outweigh its
   losses. Notebook: [`1_superiority/ESC_superiority.ipynb`](1_superiority/ESC_superiority.ipynb).
   - A tuned ESC wins on almost every plant. The reference set (k = 1, a = 0.2, f = 6 Hz) wins on 98.7 % of the 600
     plants and loses on the rest only where r_ideal is very close to 0.5, by at most 0.27 energy units; its net gain
     is 26.73 units per run (out of about 3,300).
   - ESC wins as soon as the plant's ideal ratio is farther from 0.5 than a break-even distance sqrt(L_dith / 13,225),
     a few thousandths for tuned sets (reference set: 0.0024 measured, 0.0022 predicted).
   - The size of the advantage depends on the plants assumed: about 26 units per run for the 0.45-0.55 drifting plants
     used so far, but below 1 unit for plants within 0.01 of 0.5.
   - ESC loses when the loop is about as fast as its own filters (large k at low f) or when the dither is expensive.
     Over the whole searched box ESC still wins 87.1 % of the runs, but wins outweigh losses only 2.82 times.
2. **Which ESC settings are safe and optimal, and does that depend on the plant?** Notebook:
   [`2_operating_region/ESC_operating_region.ipynb`](2_operating_region/ESC_operating_region.ipynb).
   - Proposed window: settle within 0.01 of r_ideal on every plant (also when starting at 0.3 or 0.7) within 30 s, and
     keep at least 90 % of the possible gain on every plant (the 27 sine-wave plants, which almost no setting can
     follow within 0.01, and plants with a margin below 2 units are judged separately). 142 of 2,000 random settings pass; the middle 90 % of them
     have k 0.41-2.49, a 0.026-0.383 and f 4.5-9.8 Hz. A simple rule gives nearly the same sets: lambda_avg T >= 40,
     lambda_avg / (2f) <= 0.2 and dither loss L_dith <= 0.1.
   - The reference set and the best-energy set (1.6, 0.11, 9.91) are inside the window; the three 'fastest' chosen sets
     are not (too slow on plants three times slower than nominal).
   - In normalised coordinates (lambda_avg T, lambda_avg / 2f, L_dith / margin) the window has the same shape for every
     plant family; the plant's time scale only shifts it in raw k and f. The two peaks in the gain distributions appear
     on every plant (log-uniform k through the S-curve), not on one plant only.
   - Time step: the 100 Hz loop (dt = 0.01 s) converges up to 1.67 times faster than at dt = 0.002 s (at 9.7 Hz), as the
     sampled-loop formula predicts; the region edges move by up to 0.14 decades in gain. Question for JJ.

### Longer-term goals of the project

1. **Done.** Understand the purpose and fundamentals of ESC, and build a working ESC algorithm.
2. **Ongoing.** Study the relations between the ESC parameters.
3. **Ongoing.** Use regression and classification models to predict the range of ESC parameters in which to operate.
4. **Pending.** Make the system more realistic (time-dependent loss rates, nonlinear dynamics, noise, output delays).
5. **Ongoing.** Build more ESC algorithms (discrete-time ESC, RMSprop optimiser, ...) and compare them.
6. **Pending.** Implement the controller on a physical set-up.

The proposed route from here to a publishable paper is in [`PLAN.md`](PLAN.md). It is a proposal that still needs
the supervisor's approval. [`LITERATURE_CHECK.md`](LITERATURE_CHECK.md) records whether the research question is
still open (not verified yet).

## Repository layout

| Folder / file | Contents |
|---|---|
| `Initial materials/` | Starting material from the supervisor: Simulink model, `main_fuelratio.m`, presentation. Not modified. |
| `Theory/` | `Theory summary.md`: my summary of the physics and of how ESC works, with figures. |
| `ESC/` | Single-run MATLAB scripts: `ESC.m` (basic loop), `ESC_energy.m` (drifting plant and energy), `intuition_Draft.m` (interactive exploration). |
| `1_superiority/` | Goal 1: `ESC_superiority.ipynb`, is ESC better than a fixed r = 0.5? |
| `2_operating_region/` | Goal 2: `ESC_operating_region.ipynb`, the safe and optimal ESC settings and their plant dependence. |
| `generators/` | The scripts that make the data sets, in MATLAB (`.m`) and Python (`.py`) with the same name. Each one writes into its subfolder of `data/`. |
| `data/` | All data sets (CSV), one subfolder per sweep: `STO-const_decay/`, `STO-random_decay/`, `OTO-ESC/`, `OTO-ESC_fix/`, `OTO-Plant_fix/`, `OTO-paired/`, `OTO-crossed/`. |
| `exploration/` | The notebooks. `safe-to-operate/` asks **does the ESC converge, and how fast?** (constant and random loss rates); `optimal-to-operate/` asks **how much energy does ESC give compared with a fixed ratio $r = 0.5$?** on plants whose ideal ratio drifts. |
| `checks/` | Stand-alone checks, e.g. `ESC_time_step_check.ipynb` (how the time step changes the convergence rate). |
| `Tools/` | Shared code in Python and MATLAB: the simulation (`esc_sim.py`, `esc_sim.m`) and its validation, helpers for the sweep scripts, plot style and analysis helpers (`esc_tools.py`) and classifier helpers (`esc_ml.py`). See [`Tools/README.md`](Tools/README.md). |
| `Report/` | LaTeX source of the draft report and the link to Overleaf. |
| `Papers/` | Reading list (the PDF files themselves are not kept in the repository). |
| `PLAN.md`, `LITERATURE_CHECK.md`, `SUPERVISOR_SUMMARY.md` | Next steps, the novelty check, and a short summary of the current results for the supervisor. |

## Datasets and notebooks

Every dataset is a CSV file with one row per simulated run of 100 s. The notebooks are in `exploration/`, the data
in `data/` and the scripts that made them in `generators/`. A notebook loads a file by its name only,
`esc.read_data('<file>.csv')`, which finds it anywhere under `data/`. Each notebook starts with a description of
the columns. Dataset paths below are relative to `data/`.

| Notebook | Dataset | Generated by | What varies |
|---|---|---|---|
| `exploration/safe-to-operate/STO-const_decay-200k.ipynb` | `STO-const_decay/STO-const_decay-200k.csv` | `STO_ESC_constdecay.m` | ESC parameters; constant plant |
| `exploration/safe-to-operate/STO-random_decay-200k.ipynb` | `STO-random_decay/STO-random_decay-200k.csv` | `generate_STO_random_decay.py` | ESC parameters and loss rates |
| `exploration/optimal-to-operate/OTO-ESC-10k.ipynb`, `OTO-ESC-200k.ipynb` | `OTO-ESC/OTO-ESC-10k.csv`, `OTO-ESC/OTO-ESC-200k.csv` | `OTO_ESC_rand_Plant_rand.m` | ESC parameters and drifting plant |
| `exploration/optimal-to-operate/OTO-ESC_fix.ipynb` | `OTO-ESC_fix/OTO-ESC_fix-1_0.2_6-100kshots.csv` | `OTO_ESC_fix_Plant_rand.m` | drifting plant; ESC fixed at $k=1$, $a=0.2$, $f=6$ Hz |
| `exploration/optimal-to-operate/OTO-Plant_fix.ipynb` | eight `OTO-Plant_fix/OTO-Plant_fix-<r_ideal_0>_<lambda>-100kshots.csv` | `OTO_ESC_rand_Plant_fix.m` | ESC parameters; one fixed plant per file |
| `exploration/optimal-to-operate/OTO-Plant_fix.ipynb`, Section 8 | `OTO-Plant_fix/OTO-mirror_symmetry_test.csv` | `mirror_symmetry_test.py` (Python port) | 10,000 ESC parameter sets per mirror pair; plant, twin, and twin with the dither flipped and/or the initial densities mirrored |
| `exploration/optimal-to-operate/OTO-Plant_fix-paired.ipynb` | eight `OTO-paired/OTO-paired-<r_ideal_0>_<lambda>-40k.csv` | `OTO_ESC_paired_Plant_fix.py` | the same 40,000 ESC sets on all eight fixed plants; steady start; tracking error and settling time |
| `exploration/optimal-to-operate/OTO-ESC_fix.ipynb`, Sections 6-8 | `OTO-ESC_fix/OTO-ESC_chosen-*-100k.csv`, `OTO-ESC_fix/OTO-losing_region-*.csv` | `OTO_ESC_chosen_Plant_rand.py`, `OTO_ESC_losing_region.py` | five chosen ESC sets on random drifting plants; grid of plants around $r = 0.5$ where ESC loses |
| `1_superiority/ESC_superiority.ipynb`, `2_operating_region/ESC_operating_region.ipynb` | `OTO-crossed/OTO-crossed-*.csv`: sets, plants and references tables plus 16 blocks | `OTO_ESC_crossed.py` | every one of 2,005 ESC sets (5 chosen, 2,000 quasi-random) on every one of 600 plants in seven families (static, exponential, time scale, linear, step, sine, random); steady start at 0.5; starts at 0.3 and 0.7 and a dt = 0.002 s check on subsets |

`OTO_ESC_rand_Plant_rand.m` writes `OTO-200kshots.csv`; the stored files were renamed afterwards.
In the `OTO-Plant_fix` file names, a missing `<lambda>` means no drift.

### Python versions of the sweep scripts

Every MATLAB sweep script has a Python version with the same name in `generators/` (`STO_ESC_constdecay.py`,
`STO_ESC_randdecay.py`, `OTO_ESC_rand_Plant_rand.py`, `OTO_ESC_rand_Plant_fix.py`, `OTO_ESC_fix_Plant_rand.py`).
They use the same settings, draw the random numbers in the same order from the same generator as MATLAB
(Mersenne Twister), and write the same columns. The simulation is done by `Tools/esc_sim.py`.

The MATLAB data sets were made in MATLAB sessions that did not reset the random generator, so each one starts at
a known position in MATLAB's default random stream. With `--skip <position>` the Python script draws the same
parameter sets:

| Dataset | Python script | Options |
|---|---|---|
| `STO-const_decay-200k.csv` | `STO_ESC_constdecay.py` | `--skip 726705` |
| `OTO-ESC-200k.csv` | `OTO_ESC_rand_Plant_rand.py` | (none) |
| `OTO-ESC-10k.csv` | `OTO_ESC_rand_Plant_rand.py` | `--combinations 10000 --skip 5016` |
| `OTO-ESC_fix-1_0.2_6-100kshots.csv` | `OTO_ESC_fix_Plant_rand.py` | `--skip 1812645` |
| `OTO-Plant_fix-0.5375_-0.0015-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.5375 --lambda-r-ideal -0.0015` |
| `OTO-Plant_fix-0.4625_0.0015-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.4625 --lambda-r-ideal 0.0015 --skip 300000` |
| `OTO-Plant_fix-0.5_0.001-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.5 --lambda-r-ideal 0.001 --skip 12645` |
| `OTO-Plant_fix-0.5_-0.001-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.5 --lambda-r-ideal -0.001 --skip 312645` |
| `OTO-Plant_fix-0.55_0.002-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.55 --lambda-r-ideal 0.002 --skip 612645` |
| `OTO-Plant_fix-0.45_-0.002-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.45 --lambda-r-ideal -0.002 --skip 912645` |
| `OTO-Plant_fix-0.525-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.525 --lambda-r-ideal 0 --skip 1212645` |
| `OTO-Plant_fix-0.475-100kshots.csv` | `OTO_ESC_rand_Plant_fix.py` | `--r-ideal-0 0.475 --lambda-r-ideal 0 --skip 1512645` |

Checked in November 2026: with these options the ESC and plant parameters of all rows of all twelve files are
reproduced (relative difference below $10^{-12}$, the rounding of the CSV files). For six of the files the first
2,000 to 4,000 rows were also simulated: `converged`, `convergence_time`, `choose_ESC` and `energy_const` are
identical, and `energy_ESC` is identical except for a few runs per thousand that are sensitive to rounding errors
(relative difference up to $5\times10^{-4}$). `STO_ESC_randdecay.py` has no MATLAB data set to compare with.

### MATLAB versions of the Python sweep scripts

The five sweeps that were first written in Python have a MATLAB version with the same name in `generators/`
(`OTO_ESC_paired_Plant_fix.m`, `OTO_ESC_chosen_Plant_rand.m`, `OTO_ESC_losing_region.m`, `mirror_symmetry_test.m`,
`OTO_ESC_crossed.m`).
They use `Tools/esc_sim.m`, draw the same random numbers as the Python scripts and write the same columns, to files
ending in `-matlab.csv`. `Tools/validate_matlab_ports.m` compares them with the stored data sets. `Tools/README.md`
lists which script makes which data set, in both languages.

## Conventions

- **Fuel ratio.** $r = \Gamma_T/(\Gamma_T + \Gamma_D)$ is the **tritium** fraction of the fuelling. $\hat r$ is the
  ESC's estimate of the best ratio; the applied ratio is $r = \hat r + a\sin(2\pi f t)$, clipped to $[0, 1]$.
- **Ideal ratio.** $r_\mathrm{ideal} = \alpha_T/(\alpha_T + \alpha_D)$ gives equal densities. For the nominal plant
  ($\tau_D = 1.71$ s, $\tau_T = 1.66$ s) it is about 0.507.
- **ESC parameters.** Optimizer gain $k$, dither amplitude $a$, dither frequency $f$ in Hz. Both filter cut-offs are
  tied to the dither: $\omega_c = 2\pi f/\pi$.
- **Converged.** $\hat r$ stays within 5 % of $r_\mathrm{ideal}$ for 5 s; the convergence time is the start of that
  interval.
- **Energy.** $\int n_D n_T\,dt$ over the run, with densities in $10^{19}$ m$^{-3}$.
- **Units.** Densities are in $10^{19}$ m$^{-3}$ everywhere (the factor is dropped in the code).

## Running the code

**MATLAB** (Control System Toolbox; Simulink only for `Initial materials/`). The sweep scripts in `generators/` can
be run from any folder: they add `Tools/` to the path and write their CSV file into their subfolder of `data/`
(`esc_paths('<subfolder>')`). The original sweep scripts overwrite their file as they go, so set `csv_filename`
before starting a new sweep.

**Python** 3.11 with `numpy`, `pandas`, `matplotlib`, `seaborn`, `plotly`, `scikit-learn`, `pytorch` and `jupyter`.
Open a notebook and run all cells; it finds `Tools/` by itself. To check the Python simulator against the MATLAB
data, or to regenerate the random-loss sweep:

```
python Tools/validate_esc_sim.py
python generators/generate_STO_random_decay.py
```

To run a sweep with the Python version of a MATLAB script (`--help` lists the options):

```
python generators/OTO_ESC_rand_Plant_fix.py --r-ideal-0 0.55 --lambda-r-ideal 0.002
python generators/STO_ESC_constdecay.py --combinations 1000 --output test.csv
python generators/OTO_ESC_crossed.py --parallel 8      # the crossed sweep, 8 blocks at a time
```

By default the output goes into the script's subfolder of `data/` with a name ending in `-python.csv` (`--output`
gives another path, relative to the current folder). An existing file is only replaced with `--overwrite`, so the
MATLAB data sets cannot be overwritten by accident.

**Plots.** All notebooks use one style, defined in `Tools/esc_tools.py` (`apply_style()` and `COLORS`). Change it
there to change every plot. In each notebook section the plots under **Original plots** are the ones the notebook
always had (same code, new colours and style); the plots under **Added plots** were added in November 2026 and
mostly show the same data in a more compact form. Either set can be deleted. Numbers quoted in the notebooks are
printed by the code, not typed by hand.

## Known limitations

- The plasma model is linear and first order, without noise, delays or temperature dynamics.
- The results of the two goal notebooks hold for the plant families that were chosen (`OTO-crossed-plants.csv`); the
  window thresholds (30 s, 90 % of the possible gain, margin floor of 2 units) are proposals that still need to be agreed.
- The MATLAB fixes made in November 2026 (fuelling swap in `STO_ESC_randdecay.m` and `intuition_Draft.m`) have not
  been re-run in MATLAB.
- `choose_ESC` counts any energy difference as a win, and in the optimal-to-operate sweeps many runs start inside
  the convergence band. See the notes at the end of each notebook.
- The analysis with the averaged rate $\lambda_\mathrm{avg}$ (report, Section 3.2) has not been checked by the
  supervisor yet.
