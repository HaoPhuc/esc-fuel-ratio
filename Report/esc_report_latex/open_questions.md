# Notes accompanying the report draft

All numbers in `report.tex` come from the CSVs and notebook outputs in the repository. No new simulations were run.
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

## Code / data issues
- `STO_ESC_randdecay.m`, `intuition_Draft.m`: u_D = r*S, u_T = (1-r)*S is swapped relative to r = Γ_T/(Γ_T+Γ_D). This probably explains part of the ~90 % classifier ceiling on that dataset.
- `1e-708` as the lower bound underflows to 0.
- `energy_max` (3306.25) is not attainable. The best ESC energy in any sweep is 3293.9 (99.63 %).
- `choose_ESC` has no margin. 27.5 % of OTO runs start inside the convergence band (time 0).
- The classifier outputs in `STO-const_decay-200k.ipynb` are copies of the 10k results (not re-run). `OTO-ESC-200k.ipynb` was not executed.
- `OTO_ESC_rand_Plant_fix.m` is set to plant (0.4625, 0.0015), but there is no matching CSV.
- `intuition_Draft.m`: the tune block is outside any `if`, and the analyse mode resets its history every chunk.

## Open questions / TODO in the .tex (search for `\todo`)
- Exact convergence time of the Example_ESC run. The figure should also be re-exported on a white background.
- How `alternative_convergence_time` in `appended_data.csv` was generated.
- Re-run the random-decay sweep with the swap fixed, saving the decay rates per run.
- Mirror-plant asymmetry: is it caused by the D-rich initial state or by the non-mirror exponential drift?
- Add citations for the TU/e theses and the delay / safety-filter ESC papers in `Papers/`.
- Try log(lam_avg) and log(L_dith) as classifier features.
- Add a second benchmark: fixed r at the model value r_ideal ≈ 0.507.
