"""
Vectorised Python port of the MATLAB ESC fuel-ratio simulation.

It reproduces, step for step, the loop in
    ESC/ESC.m, ESC/ESC_energy.m,
    Safe-to-operate/STO-const_decay/STO_ESC_constdecay.m,
    Optimal-to-operate/OTO_ESC_*.m
but simulates many parameter sets at once (one NumPy array element per run),
so a 200 000-run sweep takes minutes instead of hours.

Model (same symbols as the MATLAB scripts)
------------------------------------------
    dn_D/dt = -alpha_D n_D + (1 - r) S        dn_T/dt = -alpha_T n_T + r S
    S = max(0, Kp e + Ki int(e)),  e = n_ref - (n_D + n_T)       (PI density control)
    r = clip(r_hat + a sin(w t), 0, 1)                             (dither)
    P = n_D n_T  ->  high-pass s/(s+w/pi)  ->  x (2/a) sin(w t)
                 ->  low-pass (w/pi)/(s+w/pi)  ->  xi
    dr_hat/dt = k xi                                               (integrator)
All continuous blocks are discretised with a zero-order hold at dt, exactly as
MATLAB's c2d does, and the filters start from zero state like filter(..., zi=0).

Validation: see Tools/validate_esc_sim.py (compares against the MATLAB-generated
CSV files in this repository).
"""
from __future__ import annotations

import numpy as np

# ---- constants shared by every script in the repository --------------------
N_REF = 11.5                 # total density reference [1e19 m^-3]
N_GW = 11.9                  # Greenwald limit [1e19 m^-3] (plots only)
TAU_D, TAU_T = 1.71, 1.66    # nominal particle confinement times [s]
KP, KI = 3.129, 2.482        # PI gains of the total-density controller
INITIAL_RATIO = 0.1          # fuel ratio used to set the initial densities
DT, T_END = 0.01, 100.0      # time step and run length [s]
CONV_FRACTION = 0.05         # r_hat must be within 5 % of r_ideal ...
CONV_HOLD_TIME = 5.0         # ... for 5 s to count as converged
DECAY_RATE_SUM = 1 / TAU_D + 1 / TAU_T   # kept constant in the drifting plant


def _as_runs(*arrays):
    """Broadcast all inputs to 1-D float arrays of equal length (one entry per run)."""
    arrs = np.broadcast_arrays(*[np.atleast_1d(np.asarray(x, dtype=float)) for x in arrays])
    return [np.array(x, dtype=float) for x in arrs]


def simulate(optimizer_gain, dither_amplitude, dither_frequency, *,
             tau_D=TAU_D, tau_T=TAU_T,
             r_ideal_0=None, lambda_r_ideal=0.0,
             r_hat_0=0.0, use_esc=True, fixed_ratio=0.5,
             dither_phase=0.0, initial_ratio=INITIAL_RATIO, mirror_plant=False,
             dt=DT, tend=T_END, return_traces=False):
    """Simulate a batch of ESC runs.

    Plant, two modes
      * constant plant (default): loss rates 1/tau_D and 1/tau_T (scalars or one per run),
        r_ideal = alpha_T / (alpha_T + alpha_D).
      * drifting plant: pass r_ideal_0 (and lambda_r_ideal); then
        r_ideal(t) = r_ideal_0 * exp(lambda t), alpha_T = r_ideal * A,
        alpha_D = (1 - r_ideal) * A, with A = 1/1.71 + 1/1.66 (as in the OTO scripts).

    Controller
      * use_esc=True : ESC with gain k, dither amplitude a, dither frequency f [Hz],
        starting from r_hat_0.
      * use_esc=False: the fuel ratio is held at `fixed_ratio` (no dither, no optimiser).

    Options for symmetry tests (the defaults reproduce the MATLAB scripts)
      * dither_phase [rad]: the dither and the demodulation use sin(w t + dither_phase).
        With pi the first dither half-period lowers r instead of raising it.
      * initial_ratio: tritium fraction of the initial densities (MATLAB: 0.1, deuterium-rich).
      * mirror_plant=True (drifting plant only): use 1 - r_ideal_0 exp(lambda t), the exact
        mirror image of the plant (r_ideal_0, lambda) under the exchange of D and T.

    Returns a dict of arrays (one entry per run):
      converged, convergence_time [s] (NaN if not converged), energy = int n_D n_T dt,
      r_hat_final, ideal_ratio (final value for a drifting plant),
      and, if return_traces, 'traces' with t, r, r_hat, nD, nT, P, r_ideal (time x runs).
    """
    drifting = r_ideal_0 is not None
    if drifting:
        k, a, f, r0, lam, rh0 = _as_runs(optimizer_gain, dither_amplitude, dither_frequency,
                                         r_ideal_0, lambda_r_ideal, r_hat_0)
    else:
        k, a, f, tD, tT, rh0 = _as_runs(optimizer_gain, dither_amplitude, dither_frequency,
                                        tau_D, tau_T, r_hat_0)
    n_runs = k.size
    n_steps = int(round(tend / dt)) + 1
    t_vec = np.arange(n_steps) * dt
    hold = int(round(CONV_HOLD_TIME / dt))

    # --- plant (zero-order hold: x[k+1] = Ad x[k] + Bd u[k]) -----------------
    if not drifting:
        alpha_D, alpha_T = 1 / tD, 1 / tT
        ideal = alpha_T / (alpha_T + alpha_D)
        Ad_D, Ad_T = np.exp(-alpha_D * dt), np.exp(-alpha_T * dt)
        Bd_D, Bd_T = (1 - Ad_D) / alpha_D, (1 - Ad_T) / alpha_T

    # --- ESC filters (zero-order hold of s/(s+wc) and wc/(s+wc), wc = w/pi) --
    omega = 2 * np.pi * f
    p = np.exp(-(omega / np.pi) * dt)        # pole of both discrete filters
    hp_x_prev = np.zeros(n_runs); hp_y_prev = np.zeros(n_runs)   # high-pass memory
    lp_x_prev = np.zeros(n_runs); lp_y_prev = np.zeros(n_runs)   # low-pass memory
    with np.errstate(divide='ignore'):
        demod_gain = 2.0 / a

    # --- states ---------------------------------------------------------------
    nD = np.full(n_runs, 0.25 * (1 - initial_ratio) * N_REF)
    nT = np.full(n_runs, 0.25 * initial_ratio * N_REF)
    r_hat = rh0.copy()
    integral_error = np.zeros(n_runs)

    # --- bookkeeping ------------------------------------------------------------
    energy = np.zeros(n_runs); P_prev = np.zeros(n_runs)
    streak = np.zeros(n_runs, dtype=np.int64)          # consecutive in-bound samples
    streak_start = np.zeros(n_runs, dtype=np.int64)
    converged = np.zeros(n_runs, dtype=bool)
    conv_time = np.full(n_runs, np.nan)
    if return_traces:
        tr = {key: np.empty((n_steps, n_runs)) for key in ('r', 'r_hat', 'nD', 'nT', 'P', 'r_ideal')}

    for i in range(n_steps):
        t_now = t_vec[i]
        if drifting:
            ideal = r0 * np.exp(lam * t_now)
            if mirror_plant:
                ideal = 1.0 - ideal
            alpha_T = ideal * DECAY_RATE_SUM
            alpha_D = (1 - ideal) * DECAY_RATE_SUM
            Ad_D, Ad_T = np.exp(-alpha_D * dt), np.exp(-alpha_T * dt)
            Bd_D, Bd_T = (1 - Ad_D) / alpha_D, (1 - Ad_T) / alpha_T

        # fuel ratio applied to the plasma
        if use_esc:
            s = np.sin(omega * t_now + dither_phase)
            r = np.fmin(np.fmax(r_hat + a * s, 0.0), 1.0)   # like MATLAB min(max(x,0),1)
        else:
            r = np.full(n_runs, float(fixed_ratio))

        # PI controller on the total density
        e = N_REF - (nD + nT)
        integral_error += e * dt
        S_total = np.maximum(KP * e + KI * integral_error, 0.0)

        # fuelling (r is the TRITIUM fraction of the puff) and density update
        u_T = r * S_total
        u_D = (1 - r) * S_total
        nD = Ad_D * nD + Bd_D * u_D
        nT = Ad_T * nT + Bd_T * u_T
        P = nD * nT

        if use_esc:
            # high-pass: y[n] = x[n] - x[n-1] + p y[n-1]
            hp = P - hp_x_prev + p * hp_y_prev
            hp_x_prev, hp_y_prev = P, hp
            demod = hp * demod_gain * s
            # low-pass: y[n] = (1-p) x[n-1] + p y[n-1]
            xi = (1 - p) * lp_x_prev + p * lp_y_prev
            lp_x_prev, lp_y_prev = demod, xi
            # integrator k/s
            r_hat = np.fmin(np.fmax(r_hat + k * xi * dt, 0.0), 1.0)

            # convergence: first streak of `hold` samples inside the 5 % band
            in_bound = np.abs(r_hat - ideal) <= CONV_FRACTION * ideal
            streak_start = np.where(in_bound & (streak == 0), i, streak_start)
            streak = np.where(in_bound, streak + 1, 0)
            newly = (~converged) & (streak >= hold)
            conv_time[newly] = t_vec[streak_start[newly]]
            converged |= newly

        # energy = trapz(t, P)
        if i > 0:
            energy += 0.5 * (P + P_prev) * dt
        P_prev = P

        if return_traces:
            tr['r'][i], tr['r_hat'][i], tr['nD'][i], tr['nT'][i], tr['P'][i] = r, r_hat, nD, nT, P
            tr['r_ideal'][i] = ideal

    out = dict(converged=converged, convergence_time=conv_time, energy=energy,
               r_hat_final=r_hat, ideal_ratio=np.broadcast_to(ideal, (n_runs,)).copy())
    if return_traces:
        tr['t'] = t_vec
        out['traces'] = tr
    return out


def simulate_in_chunks(*args, chunk=20000, **kwargs):
    """Same as simulate(), but splits large batches to limit memory use."""
    arrs = _as_runs(*args)
    per_run_kw = {key: val for key, val in kwargs.items()
                  if key in ('tau_D', 'tau_T', 'r_ideal_0', 'lambda_r_ideal', 'r_hat_0') and np.ndim(val) > 0}
    n = arrs[0].size
    parts = []
    for start in range(0, n, chunk):
        sl = slice(start, start + chunk)
        kw = dict(kwargs); kw.update({key: np.asarray(val)[sl] for key, val in per_run_kw.items()})
        parts.append(simulate(*[x[sl] for x in arrs], **kw))
    return {key: np.concatenate([part[key] for part in parts]) for key in parts[0] if key != 'traces'}
