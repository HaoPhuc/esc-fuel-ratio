# Notes accompanying the report draft

All numbers in `report.tex` come from the CSVs and notebook outputs in the repository.
The random-loss sweep (`STO-random_decay-200k.csv`) was generated with the Python port `Tools/esc_sim.py`, which was checked against four MATLAB data sets (`Tools/validate_esc_sim.py`). All other data are from the MATLAB scripts.
The two new figures (`sto_effective_rate.png`, `oto_energy.png`) are re-plots of repository data. They use derived quantities:

- averaged ESC rate: `lam_avg = 2 * n_ref^2 * k * c(w)`, where `c(w) = |G H| cos(phi)`, `G = abar/(s+abar)`, `H = s/(s+w/pi)`, and `abar = (1/1.71 + 1/1.66)/2`
- predicted dither loss: `L_dith = T * n_ref^2/4 * 2 a^2 abar^2/(abar^2 + w^2)`

## New findings (worth discussing with the supervisor)
1. Convergence is organised by `lam_avg`. In the window 0.1–3 1/s, 96.3 % of STO-200k runs converge. The amplitude cancels to first order because of the 2/a demodulation gain. Gain and frequency trade off through c(w).
2. Supervisor defaults (k=3e-4, a=0.1, f=0.1 Hz) give a predicted t_conv ≈ 66 s. The observed value is ≈ 60 s.
3. The ESC energy gain over r=0.5 is bounded by (1-2 r_ideal)^2: ≤ 1 % for static plants in [0.45, 0.55], and up to ~5 % for the drifting plants.
4. The default dither (a=0.1, 0.1 Hz) costs ~0.94 % of the output. That is as large as the whole margin ESC can win on a static plant.
5. Tuned set k=1, a=0.2, f=6 Hz: wins on 98.4 % of 100k plants, with a worst-case loss of 0.37 units (~0.01 %).
6. Small amplitudes (a ≤ 0.05) fail occasionally even when well tuned. A likely cause is that the start-up transient gets amplified by 2/a (not verified).
7. Large amplitudes bias the estimate (new, from the random-loss sweep). With k=1, f=6 Hz and r_ideal=0.537 the estimate settles at 0.538 (a=0.2), 0.561 (a=0.6) and 0.603 (a=0.9). Inside the lam_avg window about 94 % of runs converge for a ≤ 0.5 at every r_ideal, but about 40 % for a > 0.85 with r_ideal ≥ 0.52. A likely cause is the clipping of r to [0, 1] (not verified).
8. Random loss rates: 34.9 % of 200k runs converge (36.9 % for the constant plant); 91.1 % inside the lam_avg window (96.3 %).
9. Classifiers on 200k runs reach 0.99 CV accuracy for convergence. The ~0.90 ceiling on the old random-loss data is gone with the corrected data (0.988).
10. Mirror plants do not share the same good ESC parameters: transfer accuracy is 0.787 (baseline 0.536) for the pair (0.5375, −0.0015) → (0.4625, +0.0015).

## Code / data issues (status November 2026)
- FIXED: `STO_ESC_randdecay.m`, `intuition_Draft.m` had u_D = r*S, u_T = (1-r)*S, swapped relative to r = Γ_T/(Γ_T+Γ_D). The scripts are corrected but not re-run in MATLAB. Data generated with the swapped code are removed from the report.
- FIXED: notebook outputs that were copied from another data set or never run. All notebooks were re-run.
- FIXED: the CSV named for plant (0.4625, 0.0015) contained plant (0.5375, −0.0015). It was renamed, and the (0.4625, 0.0015) plant has been simulated.
- PARTLY FIXED: `intuition_Draft.m` tune block is now inside an `if`; the analyse mode still resets its history every chunk.
- OPEN: amplitude and frequency are sampled from 0 (`1e-708` underflowed to 0 and is now written as 0), so a can be arbitrarily small.
- OPEN: `energy_max` (3306.25) is not attainable. The best ESC energy in any sweep is 3293.9 (99.63 %).
- OPEN: `choose_ESC` has no margin. 27.5 % of OTO runs start inside the convergence band (time 0).
- OPEN: the convergence label is unreliable for a ≳ 0.6 because of the bias in finding 7.

## Open questions / TODO in the .tex (search for `\todo`)
- Exact convergence time of the Example_ESC run. The figure should also be re-exported on a white background.
- Verify the clipping explanation for the large-amplitude bias on single runs.
- Re-run the corrected `STO_ESC_randdecay.m` in MATLAB as a cross-check of the Python port.
- Mirror-plant asymmetry: is it caused by the D-rich initial state or by the non-mirror exponential drift?
- Check the bibliographic details of the RMSprop-ESC paper (`mcnamee_rmsprop_esc` in `references.bib`) and of the two TU/e theses.
- Try log(lam_avg) and log(L_dith) as classifier features.
- Add a second benchmark: fixed r at the model value r_ideal ≈ 0.507.

## Sections changed in the November 2026 update (for syncing Overleaf)
- Table 1 (data sets) and the new paragraph "Python port" in the set-up section.
- Safe-to-operate results: text and caption of the pair-plot figure (now from the 200k sweep; `figures/pairplot_conv_time_lt10.png` replaced), amplitude sentence, paragraph "Random loss rates".
- Optimal-to-operate results: two sentences on the two extra plants.
- Classifier section: text and table.
- Discussion: amplitude tuning rule, list of issues, outlook items and citations.
- Conclusion: amplitude sentence.
- `references.bib`: RMSprop entry replaced; four entries added.
