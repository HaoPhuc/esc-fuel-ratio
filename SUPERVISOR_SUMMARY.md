# ESC for the D-T fuel ratio: results of the crossed sweep

25 November 2026. Simulation results in the noise-free, first-order two-species density model. Not yet reviewed.
Details and all numbers: `1_superiority/ESC_superiority.ipynb` and `2_operating_region/ESC_operating_region.ipynb`.

## What was simulated

- One data set in which every ESC setting runs on every plant (`data/OTO-crossed/`, made by
  `generators/OTO_ESC_crossed.py`; MATLAB version `OTO_ESC_crossed.m`).
- 2,005 ESC settings: the 5 settings chosen earlier, plus 2,000 quasi-random settings with k from 0.001 to 5
  (log scale), dither amplitude a from 0.005 to 0.6 and dither frequency f from 0.5 to 10 Hz.
- 600 plants in seven families: constant ideal ratio (0.40 to 0.60), exponential drift away from, towards or through
  0.5, plasma time scale x0.5, x2 and x3, linear drift, a step, a slow sine, and 364 random plants drawn as in the
  earlier sweeps (r_ideal,0 from 0.45 to 0.55, drift up to 0.002 per second).
- Runs of 100 s that start from a plasma already running at r = 0.5: 1,203,000 runs. Also starts at 0.3 and 0.7
  (30 plants), and a time-step check at dt = 0.002 s (205 settings on 50 plants).

## Claim 1: a tuned ESC beats a fixed r = 0.5

- The reference setting (k = 1, a = 0.2, f = 6 Hz) wins on 98.7 % of the 600 plants (95 % interval 97.7 to 99.5 %).
  Where it loses, r_ideal is very close to 0.5, and the largest loss is 0.27 energy units. Its net gain is 26.73
  units per 100 s run (interval 24.45 to 29.03), out of about 3,300.
- The 204 settings that are well tuned on every plant win 98.5 % of the runs (97.6 to 99.3 %), and their total wins
  are 295 times their total losses.
- Why: the gain is margin minus shortfall. The margin (best possible energy minus energy at r = 0.5) belongs to the
  plant, about 13,225 x (rms distance of r_ideal from 0.5) squared. For a tuned ESC the shortfall is its dither loss
  L_dith (measured / predicted 1.03 on the plant at 0.5). For well-tuned settings 94.0 % of the variation of the gain
  comes from the plant. So ESC wins once the plant is farther from 0.5 than sqrt(L_dith / 13,225). For the reference
  setting that is 0.0022 predicted and 0.0024 measured.
- ESC loses badly when the loop is faster than its own filters (lambda_avg above 2f: 149 settings, median net gain
  -26.14) and when k > 1 with f < 2 Hz (median net gain -76.82). Over the whole searched box ESC still wins 87.1 % of
  the runs, but its wins are only 2.82 times its losses.
- The size of the advantage depends on which plants are realistic. Well-tuned settings gain about 26 units per run
  on the random 0.45 to 0.55 plants and 10.7 on constant plants spread over 0.45 to 0.55. They gain only 0.35 on
  constant plants within 0.01 of 0.5, and 0.63 at the nominal plant (r_ideal about 0.507). The last three numbers
  are interpolated between the simulated constant plants.

## Claim 2: there is one safe and near-optimal window, the same for every plant in normalised terms

- Proposed criteria: settle within 0.01 of r_ideal on every plant within 30 s, also from starts at 0.3 and 0.7, and
  keep at least 90 % of the possible gain on every plant. The sine plants and the plants with a margin below
  2 units are judged separately.
- 142 of the 2,000 random settings pass. The middle 90 % of them have k 0.41 to 2.49, a 0.026 to 0.383 and
  f 4.5 to 9.8 Hz.
- A simple rule selects nearly the same settings (Jaccard 0.73): lambda_avg T >= 40 (fast enough), lambda_avg / 2f
  <= 0.2 (slow compared with the filters) and L_dith <= 0.1 (cheap dither).
- The reference setting and the best-energy setting (1.6, 0.11, 9.91) are inside the window. The three 'fastest'
  settings are not, because they are too slow on the plants with a time scale three times the nominal one.
- In raw (k, f) the window moves with the plant's time scale. In lambda_avg T with the plant's own loss rate, the
  lower edge of the three time-scale groups lies within 0.07 decades (0.84 decades in k). The plant's margin sets
  how cheap the dither has to be.
- The two peaks in the earlier gain distributions appear on every plant. They come from drawing k log-uniformly,
  through the S-shaped energy score, not from one particular plant.

## Limits

- No noise, delays or burn physics. Small dither amplitudes look better than they would with noise.
- The conclusions hold for the plant families we chose. The window thresholds (30 s, 90 %, margin floor 2 units) are
  proposals.
- The MATLAB versions of the new code have not been run yet (`Tools/validate_matlab_ports.m` checks them).

## Questions for JJ

1. Time step. The simulation updates every 0.01 s, so it behaves like a 100 Hz digital ESC. Compared with
   dt = 0.002 s it converges faster: 1.02 times at 1 Hz, rising to 1.67 times at 9.7 Hz. The sampled-loop formula
   Re{G(z)H(z)} predicts this within a few per cent. The edges of the window move by up to 0.14 decades in gain.
   Energies barely change. Should the study describe a 100 Hz digital ESC or a continuous one?
2. Which plants are realistic? With ideal ratios within 0.01 of 0.5 the gain is below 1 unit per run. With
   0.45 to 0.55 and drift it is about 26.
3. Are the window criteria acceptable (settle within 0.01 in 30 s, 90 % of the possible gain)?
4. Could you check the derivations of lambda_avg and of the dither loss (report sections 3.2 and 3.3)? The data agree
   with both.
