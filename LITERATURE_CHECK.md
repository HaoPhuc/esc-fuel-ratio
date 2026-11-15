# Is the research question still open?

**Status: NOT VERIFIED. To be checked by me and my supervisor before any work on `PLAN.md` starts.**

The proposed paper question (see `PLAN.md`):

> Under realistic burn dynamics, diagnostic noise and fuelling delays, when can extremum seeking control (ESC)
> find and track the optimal D–T fuelling mix better than a fixed or model-based ratio, and how should it be tuned?

The question is only worth a paper if nobody has already applied ESC (or another model-free optimiser) to the
D–T fuel mix. This file records what was searched so far, what was found, and what still has to be checked.

## 1. What has been done so far

A first search was done on 13–14 November 2026 with a general web search engine only (5 queries, listed in
Section 4). Scopus, Web of Science, IEEE Xplore and Google Scholar were **not** searched, and no citation chasing
was done. A web search can easily miss conference papers, theses and internal reports.

**Result of this first search:** no publication was found that applies extremum seeking to the D–T fuel ratio,
tritium fraction or isotope mix. This is weak evidence that the question is open. It is not proof.

## 2. Closest existing work found

### 2.1 Extremum seeking is already used in tokamaks, for other problems

| Problem | Reference | Link |
|---|---|---|
| Aligning ECCD with magnetic islands (NTM stabilisation) | "Stabilization of Neoclassical Tearing Modes in Tokamak Fusion Plasmas via Extremum Seeking", Schuster group (Lehigh), IEEE CCA 2009 | https://www6.lehigh.edu/~eus204/publications/conferences/cca09b.pdf |
| Plasma current profile (open-loop optimal control) | "Extremum-Seeking Finite-Time Optimal Control of Plasma Current Profile at the DIII-D Tokamak" | https://ieeexplore.ieee.org/document/4283102 |
| RF heating / antenna coupling on FTU | "A new extremum seeking technique and its application to maximize RF heating on FTU", Fusion Engineering and Design | https://www.sciencedirect.com/science/article/abs/pii/S0920379608004882 |
| Plasma position on FTU | "Extremum seeking applied to the plasma control system of the Frascati Tokamak Upgrade", European Control Conference 2005 | https://www.researchgate.net/publication/224628070 |
| Vertical stabilisation | "Vertical stabilization of tokamak plasmas via extremum seeking", IFAC Journal of Systems and Control 21 (2022) 100203 | https://arxiv.org/abs/2201.11708 |
| Error-field correction on DIII-D | "Error field optimization in DIII-D using extremum seeking control" | https://www.osti.gov/servlets/purl/1371745 |
| Overview of ESC applications | "100 years of extremum seeking: A survey", Automatica (2024); it lists the tokamak applications above | search by title |

So "ESC in a tokamak" is not new. Only the application to the fuel mix might be.

### 2.2 D–T mix and burn control exist, but model-based or as set-point tracking

| What it does | Reference | Link |
|---|---|---|
| Closed-loop control of the measured D:T ratio on JET, with the ratio from visible spectroscopy | "Fusion Burn Regulation via Deuterium Tritium Mixture Control in the Joint European Torus", PRX Energy 4, 023007 (2025) | https://journals.aps.org/prxenergy/abstract/10.1103/PRXEnergy.4.023007 |
| Model-based nonlinear burn control with isotopic fuel tailoring | Boyer and Schuster, "Nonlinear burn condition control in tokamaks using isotopic fuel tailoring", Nuclear Fusion 55(8), 2015 | search by title |
| **Online optimisation of the burn operating point (closest work, read first)** | Boyer and Schuster, "Nonlinear Control and Online Optimization of the Burn Condition in ITER", APS-DPP 2015 (and "Nonlinear Burn Control and Operating Point Optimization in ITER", APS-DPP 2013) | https://meetings-archive.aps.org/dpp/2015/to6/2 |
| Burn control with in-vessel coils and isotopic fuelling | Pajares and Schuster, Fusion Engineering and Design 123 (2017) 607–611 | https://www.sciencedirect.com/science/article/abs/pii/S0920379617301916 |
| Robust burn control under variations of the D–T concentration of the fuelling lines | Pajares and Schuster, IAEA FEC 2018 | https://nucleus.iaea.org/sites/fusionportal/Shared%20Documents/FEC%202018/fec2018-preprints/preprint0729.pdf |
| Adaptive burn control with uncertain actuators, confinement and recycling | Graber and Schuster, IAEA FEC 2020 | https://conferences.iaea.org/event/214/contributions/17243/ |
| Isotopic fuel tailoring as an actuator, including the effect of recycling | Schuster, in IAEA TECDOC-2049 | https://www-pub.iaea.org/MTCD/Publications/PDF/TE-2049web.pdf |
| Why a mix other than 50:50 can be preferable (tritium burn efficiency) | "Simultaneous enhancement of tritium burn efficiency and fusion power with low-tritium spin-polarized fuel", Nuclear Fusion (2024) | https://arxiv.org/abs/2406.05970 |

What these have in common: they need either a measurement of the isotope ratio or a plasma model (often with
adaptive estimation of uncertain parameters). None of the pages found describes a perturbation-based, model-free
search for the best mix using only the neutron rate.

**The item to read most carefully** is the "online optimization of the burn condition" work of Boyer and Schuster.
If its optimiser already finds the best tritium fraction in real time, the novelty left for this project is the
*model-free* route and its behaviour under noise and delay, and the paper has to be framed that way.

### 2.3 Method papers relevant to the planned steps

| Topic | Reference | Link |
|---|---|---|
| ESC with (time-varying) delays | Santos and Oliveira, "Gradient Extremum Seeking With Nonconstant Delays", IEEE Access 2020 | https://doi.org/10.1109/ACCESS.2020.3005186 |
| ESC under sensor noise | "Sensor-Noise Mitigation in Extremum Seeking Control Using Adaptive Numerical Differentiation" (preprint) | https://arxiv.org/abs/2501.04275 |
| Safe ESC with constraints | Williams, Krstic and Scheinker, "Semiglobal Safety-Filtered Extremum Seeking With Unknown CBFs", IEEE TAC 70(3), 2025 | search by title |

## 3. Verification worksheet (to do)

Tick each line when done and write the outcome next to it.

### 3.1 Database searches

Run each search string in **Scopus or Web of Science**, **IEEE Xplore** and **Google Scholar**. Record the number of
hits and any relevant paper.

| # | Search string | Scopus / WoS | IEEE Xplore | Google Scholar | Relevant hits |
|---|---|---|---|---|---|
| 1 | `"extremum seeking" AND (tokamak OR fusion) AND (fuel* OR tritium OR isotop* OR "burn control")` | ☐ | ☐ | ☐ | |
| 2 | `("model-free" OR "data-driven" OR "self-optimizing" OR "real-time optimization") AND ("tritium fraction" OR "isotope mix" OR "fuel mix" OR "D-T ratio") AND control` | ☐ | ☐ | ☐ | |
| 3 | `("burn control" OR "fusion power control") AND (optimi* OR "extremum" OR "perturb*") AND ("isotopic" OR "tritium fraction")` | ☐ | ☐ | ☐ | |
| 4 | `("neutron rate" OR "fusion power") AND (maximi* OR optimi*) AND (dither OR perturbation OR modulation) AND (fuelling OR fueling)` | ☐ | ☐ | ☐ | |
| 5 | `"isotope mix control" OR "isotope ratio control" AND (ITER OR DEMO OR JET)` | ☐ | ☐ | ☐ | |

### 3.2 Citation chasing

Open the "cited by" list of each paper and scan the titles for extremum seeking, model-free or optimisation.

- ☐ JET D–T mixture control, PRX Energy 4, 023007 (2025)
- ☐ Boyer and Schuster, Nuclear Fusion 55(8), 2015 (isotopic fuel tailoring)
- ☐ Pajares and Schuster, Fusion Engineering and Design 123 (2017)
- ☐ "100 years of extremum seeking: A survey", Automatica 2024: check its fusion section and reference list
- ☐ The two TU/e bachelor theses on the physical ESC test set-up (see `Papers/README.md`): what application do they
  name, and do they cite earlier fuel-ratio work?

### 3.3 People to ask

- ☐ Supervisor (Juan Javier Palacios Roman): where did the fuel-ratio ESC idea and the Simulink model come from?
  Is there earlier DIFFER or TU/e work (published, a thesis, or internal) on exactly this?
- ☐ DIFFER mentor: is anyone in the group or at ITER/EUROfusion working on isotope-mix optimisation?
- ☐ Is a paper or thesis by the group already planned on this topic (authorship and overlap)?

## 4. Searches done so far (web search engine only)

1. `extremum seeking control deuterium tritium fuel ratio tokamak`
2. `extremum seeking burn control isotopic fueling neutron rate optimization`
3. `"extremum seeking" tokamak fusion plasma control application`
4. `"extremum seeking" tritium fraction OR "isotope mix" OR "fuel mix" fusion power optimization`
5. `burn control tritium fraction optimization isotopic fuel tailoring adaptive uncertain recycling Schuster`

(Queries 1 and 2 were run on 13 November, 3 to 5 on 14 November 2026. Programmatic searches of CrossRef and
arXiv were attempted but the network was unavailable.)

## 5. Decision

| Outcome of the check | Consequence for the plan |
|---|---|
| Nothing found on ESC or model-free optimisation of the fuel mix | Go ahead with `PLAN.md` as written. State the gap explicitly in the introduction, with the references of Section 2. |
| Model-based online optimisation of the tritium fraction exists (for example Boyer and Schuster), but nothing model-free | Go ahead, but frame the paper as "model-free versus model-based" and make the comparison of Step 4 the core. |
| A paper already applies ESC to the fuel mix | Do not repeat it. Narrow the question to what that paper leaves out (noise and delay limits, tritium economy, tracking a drifting optimum), or keep the work as an internship report. |

**Decision (fill in):** ☐ open ☐ partly open ☐ not open — date: ________ — checked by: ________
