# Handoff: state of the work (16 November 2026)

This file is for whoever continues the analysis (a person or an AI assistant). It lists what was done last, what
was decided, and what is still open. Read `README.md` first for the layout of the repository.

## Latest work: the paired fixed-plant sweep

**Files**
- `Optimal-to-operate/OTO_ESC_paired_Plant_fix.py`: generates the data (about 15 min with one process per plant;
  start eight `--plant <i>` runs side by side, because Python multiprocessing does not work in every environment).
- `Optimal-to-operate/OTO-paired-<plant>-40k.csv` (8 files): the same 40,000 ESC sets on each of the eight fixed plants.
- `Optimal-to-operate/OTO-Plant_fix-paired.ipynb`: the analysis. Its Notes cell lists the results and limits.
- `Tools/esc_sim.py`: new options `steady_start`, `ratio_map`, `track`, `settle_tolerances` and
  `fixed_ratio='ideal'` (see its docstring). The defaults still reproduce the MATLAB data exactly.

**Design decisions (agreed with the user)**
- Same ESC sets on every plant, so a set can be judged by its worst plant.
- Sampling only where ESC is useful: $k$ 0.02 to 5 (log-uniform), $a$ 0 to 0.6, $f$ 1.5 to 10 Hz.
- Runs start from a plasma that is already running (full density, steady state at $r = 0.5$). The old start
  (25 % density, deuterium-rich) does not occur in practice and caused most of the differences between mirror plants.
- Energy score $\eta = (E_\mathrm{ESC} - E_{r=0.5}) / (E_\mathrm{ideal} - E_{r=0.5})$, with $E_\mathrm{ideal}$ the energy
  when the ratio follows $r_\mathrm{ideal}(t)$ exactly.
- Speed is measured on the ratio the plasma receives (not on the estimate $\hat r$), averaged over a whole number of
  dither periods (closest to 1 s). An earlier version averaged over exactly 1 s; that left dither ripple in the
  measure and was replaced on 16 November (the CSV files were regenerated).

**Proposals that still need the supervisor's agreement**
- Group limits: $\eta \ge 0.9$ (A), 0.5 (B), 0.1 (C); settling tolerances 0.01 and 0.02 (about 0.04 % and 0.16 %
  of the power).
- Judging a set by its worst plant.

## Open points, in order of priority

1. **Received versus requested ratio.** The supervisor has a function that relates the ratio the plasma receives
   to the ratio that is requested. It has not been obtained yet. When it is: implement it as the `ratio_map`
   argument of `esc_sim.simulate` (a function from the requested ratio array to the received ratio array), rerun
   `OTO_ESC_paired_Plant_fix.py`, and re-execute the notebook. At present the received ratio is the requested ratio
   clipped to [0, 1].
2. **Measurement noise.** Without noise the fastest sets use very small dither amplitudes ($a$ down to 0.02). Add a
   noise term to the measured $n_D n_T$ in `esc_sim.simulate` before recommending an amplitude.
3. **Report.** `Report/esc_report_latex/` does not contain the results of the paired sweep or of the mirror
   symmetry test (Section 8 of `OTO-Plant_fix.ipynb`). The statement that large dither amplitudes "bias the
   estimate" should be reworded: the estimate is off, but the ratio the plasma receives is at its optimum.
4. **Old notebooks.** The other notebooks still use the old convergence measure on $\hat r$ and the 25 % start.
   Their conclusions on speed should be read with that in mind (see the Notes of the paired notebook).
5. `PLAN.md` and `LITERATURE_CHECK.md` still wait for the supervisor's sign-off.

## Practical notes

- The user commits the work themselves; leave changes uncommitted.
- Never write helper output into the data folders unless it is meant to stay there.
- Notebooks: each one finds `Tools/` by itself; run all cells from top to bottom.
