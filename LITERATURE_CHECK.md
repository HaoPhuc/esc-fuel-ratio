Is the idea new? (literature check)

Status: NOT VERIFIED yet. Me and my supervisor still have to check this before starting on PLAN.md.

The question:
- can ESC find and follow the best D-T fuel mix, using only the neutron rate, better than a fixed 50:50 mix or a model-based ratio, with realistic noise and delays? and how should it be tuned?
- only worth a paper if nobody already used ESC (or another model-free optimiser) on the D-T fuel mix

What I did so far:
- only a quick web search on 13-14 Nov 2026, 5 searches (listed at the bottom)
- did not search Scopus, Web of Science, IEEE Xplore or Google Scholar, and did not look at "cited by" lists
- found nothing that uses ESC on the D-T ratio, tritium fraction or isotope mix
- this is weak evidence that the idea is new, not proof (a web search easily misses conference papers, theses, internal reports)

ESC is already used in tokamaks, but for other problems (so "ESC in a tokamak" is not new):
- NTM stabilisation, aligning ECCD with the islands: Schuster group (Lehigh), IEEE CCA 2009, https://www6.lehigh.edu/~eus204/publications/conferences/cca09b.pdf
- plasma current profile at DIII-D: "Extremum-Seeking Finite-Time Optimal Control of Plasma Current Profile at the DIII-D Tokamak", https://ieeexplore.ieee.org/document/4283102
- RF heating on FTU: "A new extremum seeking technique and its application to maximize RF heating on FTU", Fusion Engineering and Design, https://www.sciencedirect.com/science/article/abs/pii/S0920379608004882
- plasma position on FTU: European Control Conference 2005, https://www.researchgate.net/publication/224628070
- vertical stabilisation: IFAC Journal of Systems and Control 21 (2022) 100203, https://arxiv.org/abs/2201.11708
- error-field correction on DIII-D: https://www.osti.gov/servlets/purl/1371745
- overview: "100 years of extremum seeking: A survey", Automatica 2024 (lists the ones above)

D-T mix and burn control already exist, but they need a model or a measurement of the isotope ratio:
- JET: closed-loop control of the D:T ratio measured with spectroscopy, "Fusion Burn Regulation via Deuterium Tritium Mixture Control in the Joint European Torus", PRX Energy 4, 023007 (2025), https://journals.aps.org/prxenergy/abstract/10.1103/PRXEnergy.4.023007
- Boyer and Schuster, "Nonlinear burn condition control in tokamaks using isotopic fuel tailoring", Nuclear Fusion 55(8), 2015
- CLOSEST WORK, read first: Boyer and Schuster, "Nonlinear Control and Online Optimization of the Burn Condition in ITER", APS-DPP 2015 (and APS-DPP 2013), https://meetings-archive.aps.org/dpp/2015/to6/2
  - if their optimiser already finds the best tritium fraction in real time, then what is new here is only the model-free part and how it behaves with noise and delay
- Pajares and Schuster, burn control with in-vessel coils and isotopic fuelling, Fusion Engineering and Design 123 (2017) 607-611, https://www.sciencedirect.com/science/article/abs/pii/S0920379617301916
- Pajares and Schuster, robust burn control when the D-T mix of the fuelling lines varies, IAEA FEC 2018, https://nucleus.iaea.org/sites/fusionportal/Shared%20Documents/FEC%202018/fec2018-preprints/preprint0729.pdf
- Graber and Schuster, adaptive burn control with uncertain actuators, confinement and recycling, IAEA FEC 2020, https://conferences.iaea.org/event/214/contributions/17243/
- Schuster, isotopic fuel tailoring as an actuator (incl. recycling), IAEA TECDOC-2049, https://www-pub.iaea.org/MTCD/Publications/PDF/TE-2049web.pdf
- why a mix other than 50:50 can be better (tritium burn efficiency): Nuclear Fusion 2024, https://arxiv.org/abs/2406.05970
- none of these is a model-free, dither-based search for the best mix using only the neutron rate

Method papers that might help later:
- ESC with changing delays: Santos and Oliveira, "Gradient Extremum Seeking With Nonconstant Delays", IEEE Access 2020, https://doi.org/10.1109/ACCESS.2020.3005186
- ESC with sensor noise: "Sensor-Noise Mitigation in Extremum Seeking Control Using Adaptive Numerical Differentiation", https://arxiv.org/abs/2501.04275
- safe ESC with constraints: Williams, Krstic and Scheinker, "Semiglobal Safety-Filtered Extremum Seeking With Unknown CBFs", IEEE TAC 70(3), 2025

Still to do:
- search Scopus or Web of Science, IEEE Xplore and Google Scholar, write down hits:
  - extremum seeking + tokamak/fusion + fuel/tritium/isotope/burn control
  - model-free/data-driven/real-time optimisation + tritium fraction/isotope mix/fuel mix/D-T ratio + control
  - burn control/fusion power control + optimisation/extremum/perturbation + isotopic/tritium fraction
  - neutron rate/fusion power + maximise/optimise + dither/perturbation/modulation + fuelling
  - isotope mix control/isotope ratio control + ITER/DEMO/JET
- look through the "cited by" lists of:
  - the JET paper (PRX Energy 2025)
  - Boyer and Schuster, Nuclear Fusion 2015
  - Pajares and Schuster, FED 2017
  - the ESC survey (Automatica 2024), its fusion part and references
  - the two TU/e bachelor theses on the ESC test set-up (Papers/README.md): what application do they name, do they cite earlier fuel-ratio work?
- ask supervisor (Juan Javier Palacios Roman): where did the fuel-ratio ESC idea and the Simulink model come from? earlier DIFFER or TU/e work on this?
- ask DIFFER mentor: is anyone (DIFFER, ITER, EUROfusion) working on isotope-mix optimisation?
- ask: is a paper or thesis on this already planned by the group (overlap, authorship)?

What to do depending on the result:
- nothing found -> go ahead with PLAN.md, say clearly in the introduction that this is a gap
- model-based online optimisation of the tritium fraction exists (e.g. Boyer and Schuster), but nothing model-free -> go ahead, but frame it as model-free vs model-based
- someone already used ESC on the fuel mix -> don't repeat it; focus on what they left out (noise, delay, tritium cost, drifting optimum), or keep it as an internship report

Web searches done so far (13 Nov: 1-2, 14 Nov: 3-5):
- extremum seeking control deuterium tritium fuel ratio tokamak
- extremum seeking burn control isotopic fueling neutron rate optimization
- "extremum seeking" tokamak fusion plasma control application
- "extremum seeking" tritium fraction OR "isotope mix" OR "fuel mix" fusion power optimization
- burn control tritium fraction optimization isotopic fuel tailoring adaptive uncertain recycling Schuster

Decision: open / partly open / not open, date: ____, checked by: ____
