# Plan: from internship project to a publishable paper

**Status: PROPOSAL. Nothing below has been approved. Each step has a sign-off line for the supervisor.**

Legend: ☐ to do · ☑ done · ⏸ waiting for a decision

## Where the project stands (November 2026)

- A working ESC loop on a first-order two-species density model (MATLAB), and a Python simulator that reproduces
  it exactly (`Tools/esc_sim.py`).
- Large random sweeps over the ESC parameters, analysed in the notebooks (see `README.md`).
- A draft report (`Report/`). Its main results: convergence is governed by one combined rate $\lambda_\mathrm{avg}$;
  the dither costs energy at low dither frequency; ESC beats a fixed ratio $r = 0.5$ mainly when the ideal ratio is
  uncertain or drifts.
- Honest assessment: these results follow from standard ESC averaging theory on a deliberately simple plant.
  As it stands this is a good internship report, not a journal paper.

## Proposed paper question

> Under realistic burn dynamics, diagnostic noise and fuelling delays, when can extremum seeking find and track
> the optimal D–T fuelling mix better than a fixed or model-based ratio, and how should it be tuned?

A negative answer ("ESC only wins under these conditions") would also be a result, because it sets out the limits
of the method.

---

## Step 0. Check that the question is open

**Goal.** Make sure nobody has already published ESC (or another model-free optimiser) for the D–T fuel mix.

- ☐ Work through `LITERATURE_CHECK.md` (database searches, citation chasing, people to ask).
- ☐ Read the closest work first: Boyer and Schuster, online optimisation of the burn condition in ITER.
- ☐ Fill in the decision at the bottom of `LITERATURE_CHECK.md`.

**Done when:** the decision table in `LITERATURE_CHECK.md` is filled in and the supervisor agrees.

**Questions for the supervisor**
1. Where did the fuel-ratio ESC idea come from, and is there earlier DIFFER or TU/e work on it?
2. Is a publication a realistic goal for this project, and who would be co-authors?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 1. Consolidate the simple-plant results into a validated baseline

**Goal.** Turn the current work into the "baseline" section of the paper: the averaging theory explains the simple
plant, so later deviations from it can be trusted.

- ☑ Fix the deuterium/tritium swap in `STO_ESC_randdecay.m` and `intuition_Draft.m` (MATLAB edits not re-run yet).
- ☑ Remove the datasets generated with the swapped code; regenerate the random-loss sweep.
- ☑ Port the simulation to Python and validate it against the MATLAB datasets.
- ☑ Re-run every notebook on its own dataset with one plot style.
- ☐ Supervisor checks the derivation of $\lambda_\mathrm{avg}$ and the dither loss (report, Sections 3.2 and 3.3).
- ☐ Validate both formulas on single runs: convergence time and steady-state ripple against $k$, $a$, $f$.
- ☐ Replace the 200k random sweeps by a small designed sweep (Latin hypercube or grid, 1–5k runs) around the
  predicted tuning window, with fixed random seeds and confidence intervals on every reported fraction.
- ☐ Make the outcome labels meaningful: a margin on `choose_ESC` (for example a gain above 0.1 %), and a convergence
  criterion that does not count runs that start inside the band.
- ☐ Explain the large-amplitude bias found in `STO-random_decay-200k.ipynb` (estimate settles away from the ideal
  ratio when $a > 0.5$; probably the clipping of $r$ to $[0, 1]$).
- ☐ Decouple the filter cut-offs from the dither frequency and include them in the sweep.

**Deliverables.** One notebook or script per baseline figure; updated report Sections 3 to 5.

**Done when:** the predicted tuning window matches the designed sweep within its confidence intervals.

**Questions for the supervisor**
1. Is the averaging argument correct, and is it fine to present it as "standard theory applied to this plant"?
2. Should further sweeps be run in MATLAB, or is the validated Python simulator acceptable?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 2. Replace the plant by a 0-D burn model

**Goal.** Make the optimum non-trivial, so that a model-free optimiser has something to find.

- ☐ Choose a published volume-averaged burn model to build on (candidates: the models used by Schuster's group for
  ITER burn control; ask DIFFER whether a 0-D model is available).
- ☐ Implement: energy balance, $n_D$, $n_T$, helium ash, impurities, temperature-dependent $\langle\sigma v\rangle$
  (Bosch–Hale), alpha heating.
- ☐ Add isotope-specific wall retention and recycling with slow time constants, so that the best fuelling mix
  drifts during a pulse.
- ☐ Check the model against published operating points before adding any controller.
- ☐ Show how the optimal fuelling ratio depends on the uncertain parameters and how it drifts.

**Deliverables.** `burn_model` code with tests; a figure of the optimal mix against time and against the uncertain
parameters.

**Done when:** the model reproduces at least one published operating point, and the optimal fuelling ratio is
demonstrably not a fixed, known number.

**Questions for the supervisor**
1. Which burn model and which machine parameters (ITER, a DEMO-like device, JET D–T) should be used?
2. How detailed must recycling be for the result to be credible?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 3. Realistic sensing and actuation (expected core contribution)

**Goal.** Find the tuning window when the measurement is noisy and delayed and the actuator is slow.

- ☐ Neutron-rate measurement: counting noise, calibration drift, sampling rate.
- ☐ Delays: diagnostic delay, gas-valve dynamics, time for edge-fuelled gas to reach the core.
- ☐ Limits: range of the tritium fraction, maximum fuelling rate.
- ☐ Re-derive the tuning window with noise and delay, and compare with simulation.
- ☐ Test whether the current conclusion "use a high dither frequency" survives. It probably does not: noise and
  delay make high frequencies costly.
- ☐ Compare with ESC variants made for delays and noise (see `Papers/README.md`).

**Deliverables.** A figure of the tuning window against noise level and delay, theory against simulation.

**Done when:** there is a tuning rule that states the usable dither frequency and gain as functions of noise level
and delay, checked in simulation.

**Questions for the supervisor**
1. What are realistic numbers for neutron-diagnostic noise and delay, and for gas-valve response?
2. Is pellet fuelling (discrete actuator) in scope, or gas puffing only?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 4. Compare against fair alternatives

**Goal.** Answer "compared to what?".

- ☐ Fixed ratio $r = 0.5$.
- ☐ Fixed ratio from a model with deliberately wrong loss and recycling parameters.
- ☐ Feedback on a measured D:T ratio with measurement error (the JET approach).
- ☐ At least one improved ESC variant: Newton-based, discrete-time, adaptive dither, or RMSprop-ESC.
- ☐ Metrics: fusion energy, time to reach the optimum, tracking error under drift, tritium injected, robustness
  over many plant realisations.

**Deliverables.** A comparison table and figure over many plant realisations, with confidence intervals.

**Done when:** for each controller it is clear in which conditions it wins or loses.

**Questions for the supervisor**
1. Which baseline would a fusion-control reviewer expect?
2. Is implementing a model-based controller in scope, or can a simplified version stand in for it?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 5. Tritium economy as the objective

**Goal.** Give the optimiser an objective whose optimum is not 50:50.

- ☐ Optimise $J = P_\mathrm{fus} - w\,\Gamma_T$ (fusion power penalised by tritium injection).
- ☐ Show how the optimum shifts with the weight $w$ and with the unknown plant parameters.
- ☐ Plot the trade-off between energy and tritium used for each controller.

**Deliverables.** Trade-off figure (energy against tritium used) with the operating points of each controller.

**Done when:** the trade-off curve is produced and ESC's position on it is understood.

**Questions for the supervisor**
1. Is tritium economy a convincing motivation, or is another objective (for example fusion gain $Q$) better?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## Step 6. Validation (optional, strengthens a journal version)

- ☐ Either run the controller on the physical ESC test set-up with the plant simulated in real time,
- ☐ or drive the burn model with parameters from published JET D–T scenarios.

**Questions for the supervisor**
1. Is the test set-up available, and is this realistic within the project time?

Sign-off: ☐ approved ☐ change needed — name / date: ____________________ — notes:

---

## What to do with the machine-learning part

The classifiers predict what two formulas ($\lambda_\mathrm{avg}$ and the dither loss) already predict. Options:

- ☐ **Surrogate model.** With the burn model and noise each simulation is expensive. Train a model to predict
  energy, convergence and tritium use, and use it for robust tuning (for example Bayesian optimisation).
- ☐ **Physics-informed features.** Show that $\log\lambda_\mathrm{avg}$ and $\log L_\mathrm{dith}$ as inputs beat the
  raw parameters with a smaller network.
- ☐ Otherwise move the machine learning to an appendix.

Decision: ⏸ — notes:

## Planned figures of the paper

1. Schematic: plant, diagnostics, ESC loop and the comparison controllers.
2. Baseline: averaging theory predicts the simple-plant sweep.
3. Burn model: the optimal fuel mix drifting with wall saturation, and its sensitivity to uncertain parameters.
4. Tuning window under noise and delay, theory against simulation.
5. Controller comparison over many plant realisations.
6. Energy–tritium trade-off with each controller's operating point.

## Working rules for the paper phase

- Fixed random seeds and designed sampling; confidence intervals on every reported fraction.
- Store every randomised plant parameter with each run.
- One script or notebook per paper figure, regenerating it from saved data.
- Numbers in text are printed by code, never typed by hand.
- Tag a release of the repository for every submitted version.

## Possible venues (to discuss)

- A control conference (CDC, ACC, ECC or IEEE CCTA) for Steps 1 to 4.
- SOFT or *Fusion Engineering and Design* for the version with the realistic plant and tritium economy.
- A student or national physics meeting poster from Step 1 alone.
