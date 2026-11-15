# Reading list

The PDF files that used to be in this folder and in `Theory/` were removed from the repository because they are
copyrighted (they are still in the git history). This list says what they were and where to get them.
Papers found during the literature check are in `LITERATURE_CHECK.md`.

## Background

| Reference | Used for | Where to find it |
|---|---|---|
| J. Wesson, *Tokamaks*, 3rd edition, Oxford University Press, 2004 | Tokamak physics background (fusion power, density limit) | University library |
| K. B. Ariyur and M. Krstić, *Real-Time Optimization by Extremum-Seeking Control*, Wiley, 2003 | Standard ESC textbook; averaging analysis | University library |
| M. Krstić and H.-H. Wang, "Stability of extremum seeking feedback for general nonlinear dynamic systems", *Automatica* 36(4), 595–601, 2000 | Stability proof behind the ESC loop used here | Search by title |

## ESC methods to compare with later (see `PLAN.md`, Steps 3 and 4)

| Reference | Used for | Where to find it |
|---|---|---|
| G. C. Santos and T. R. Oliveira, "Gradient Extremum Seeking With Nonconstant Delays", *IEEE Access*, 2020 | ESC when the measurement or actuator is delayed | https://doi.org/10.1109/ACCESS.2020.3005186 (open access) |
| P. McNamee and Z. Nili Ahmadabadi, "Adaptive Extremum Seeking Control via the RMSprop Optimizer" | RMSprop-based ESC with a normalised convergence rate | Search by title (publication venue not checked yet) |
| A. Williams, M. Krstić and A. Scheinker, "Semiglobal Safety-Filtered Extremum Seeking With Unknown CBFs", *IEEE Transactions on Automatic Control* 70(3), from p. 1698, March 2025 | ESC that respects a safety constraint (for example the density limit) | Search by title |

## Physical test set-up at TU/e

| Reference | Used for | Where to find it |
|---|---|---|
| A. Varnavides, "Preparation of Experimental Setup", bachelor thesis, Eindhoven University of Technology, 2025 | Hardware set-up for testing ESC | TU/e student theses repository (research.tue.nl) |
| N. E. de Korte, "Implementing extremum seeking control on a physical testing setup", bachelor thesis, Eindhoven University of Technology, 2026 | ESC implemented on that set-up | TU/e student theses repository (research.tue.nl) |

## Still in the repository

- `Theory/Theory summary.md`: my own summary of the theory.
- `Theory/FourierLaplacez-Transforms.pdf`: 13 scanned pages on Fourier, Laplace and z-transforms. Its source is
  not recorded. **To decide:** keep it only if these are my own notes or freely shareable material.
