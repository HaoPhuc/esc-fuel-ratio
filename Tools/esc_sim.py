"""
Vectorised Python port of the MATLAB ESC fuel-ratio simulation.

It reproduces, step for step, the loop in
    ESC/ESC.m, ESC/ESC_energy.m,
    generators/STO_ESC_constdecay.m,
    generators/OTO_ESC_*.m
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
DRIFT_SHAPES = {'exp': 0, 'linear': 1, 'step': 2, 'sine': 3}   # codes of the drift_shape option


def _as_runs(*arrays):
    """Broadcast all inputs to 1-D float arrays of equal length (one entry per run)."""
    arrs = np.broadcast_arrays(*[np.atleast_1d(np.asarray(x, dtype=float)) for x in arrays])
    return [np.array(x, dtype=float) for x in arrs]


def drift_codes(drift_shape):
    """drift_shape as numbers: a name ('exp', 'linear', 'step', 'sine'), a list of names or codes 0-3."""
    shape = np.asarray(drift_shape)
    if shape.dtype.kind in 'US':
        return np.vectorize(DRIFT_SHAPES.__getitem__, otypes=[float])(shape)
    return shape.astype(float)


def simulate(optimizer_gain, dither_amplitude, dither_frequency, *,
             tau_D=TAU_D, tau_T=TAU_T, tau_scale=1.0,
             r_ideal_0=None, lambda_r_ideal=0.0, drift_shape='exp', drift_size=0.0, drift_time=None,
             r_hat_0=0.0, use_esc=True, fixed_ratio=0.5,
             dither_phase=0.0, initial_ratio=INITIAL_RATIO, mirror_plant=False,
             steady_start=None, ratio_map=None, track=False, settle_tolerances=(0.01, 0.02),
             dt=DT, tend=T_END, return_traces=False):
    """Simulate a batch of ESC runs.

    Plant, two modes
      * constant plant (default): loss rates 1/tau_D and 1/tau_T (scalars or one per run),
        r_ideal = alpha_T / (alpha_T + alpha_D).
      * drifting plant: pass r_ideal_0 (and lambda_r_ideal); then
        r_ideal(t) = r_ideal_0 * exp(lambda t), alpha_T = r_ideal * A,
        alpha_D = (1 - r_ideal) * A, with A = 1/1.71 + 1/1.66 (as in the OTO scripts).

    Options added for the crossed plant x ESC sweep (the defaults change nothing)
      * tau_scale: both confinement times are multiplied by this factor (scalar or one per run),
        so the plasma reacts slower (> 1) or faster (< 1); r_ideal does not change.
      * drift_shape, drift_size (D), drift_time (T_d, default tend), drifting plant only, one per run allowed:
          'exp'    r_ideal(t) = r_ideal_0 exp(lambda t)               (default; D and T_d are not used)
          'linear' r_ideal(t) = r_ideal_0 + D t / T_d                  (D = change after T_d)
          'step'   r_ideal(t) = r_ideal_0 + D for t >= T_d, else r_ideal_0
          'sine'   r_ideal(t) = r_ideal_0 + D sin(2 pi t / T_d)        (T_d = period)
        lambda_r_ideal still multiplies r_ideal_0 by exp(lambda t) for the other shapes; use 0 there.

    Controller
      * use_esc=True : ESC with gain k, dither amplitude a, dither frequency f [Hz],
        starting from r_hat_0.
      * use_esc=False: the fuel ratio is held at `fixed_ratio` (no dither, no optimiser).
        fixed_ratio='ideal' makes the ratio follow r_ideal(t) exactly (reference for the best possible energy).

    Options for symmetry tests (the defaults reproduce the MATLAB scripts)
      * dither_phase [rad]: the dither and the demodulation use sin(w t + dither_phase).
        With pi the first dither half-period lowers r instead of raising it.
      * initial_ratio: tritium fraction of the initial densities (MATLAB: 0.1, deuterium-rich).
      * mirror_plant=True (drifting plant only): use 1 - r_ideal_0 exp(lambda t), the exact
        mirror image of the plant (r_ideal_0, lambda) under the exchange of D and T.

    Options added for the paired fixed-plant sweep (the defaults reproduce the MATLAB scripts)
      * steady_start: if a ratio is given (e.g. 0.5), the run starts from a plasma that is already
        running: full density n_ref, in steady state with that fuel ratio, density controller and
        high-pass filter at rest. Default None: 25 % density, set with `initial_ratio`, as in MATLAB.
      * ratio_map: function from the REQUESTED ratio (r_hat + dither) to the ratio the plasma RECEIVES.
        Default: clipping to [0, 1]. Placeholder for the relation the supervisor described; replace it
        when that relation is known.
      * track=True adds measures based on the received ratio, averaged over a whole number of dither
        periods (the number closest to 1 s, at least one period), so that the dither itself cancels:
          tracking_error       mean |received - r_ideal| over the run (after the first second)
          tracking_error_late  the same over the second half of the run
          settling_time_<tol>  time after which |received - r_ideal| stays below tol until the end of
                               the run [s]; NaN if it is exceeded in the last 5 s. One entry per value
                               in settle_tolerances.

    Returns a dict of arrays (one entry per run):
      converged, convergence_time [s] (NaN if not converged), energy = int n_D n_T dt,
      r_hat_final, ideal_ratio (final value for a drifting plant),
      and, if return_traces, 'traces' with t, r, r_hat, nD, nT, P, r_ideal (time x runs).
    """
    drifting = r_ideal_0 is not None
    if drift_time is None:
        drift_time = tend
    if drifting:
        k, a, f, r0, lam, rh0, scale, shape, size, t_drift = _as_runs(
            optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, r_hat_0,
            tau_scale, drift_codes(drift_shape), drift_size, drift_time)
        decay_rate_sum = DECAY_RATE_SUM / scale          # A of the drifting plant, one per run
        shaped = bool(np.any(shape != 0))                 # any run with a linear, step or sine drift

        def ideal_at(t_now):
            """r_ideal of every run at time t_now (also used for the steady start)."""
            value = r0 * np.exp(lam * t_now)
            if shaped:
                g = np.where(shape == 1, t_now / t_drift,
                             np.where(shape == 2, (t_now >= t_drift).astype(float),
                                      np.where(shape == 3, np.sin(2 * np.pi * t_now / t_drift), 0.0)))
                value = value + size * g
            return 1.0 - value if mirror_plant else value
    else:
        k, a, f, tD, tT, rh0, scale = _as_runs(optimizer_gain, dither_amplitude, dither_frequency,
                                               tau_D, tau_T, r_hat_0, tau_scale)
        tD, tT = tD * scale, tT * scale
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
    if steady_start is not None:
        # plasma already running at the ratio `steady_start`: total density n_ref, nothing changes in time
        if drifting:
            ideal_0 = ideal_at(0.0)
            alpha_T0, alpha_D0 = ideal_0 * decay_rate_sum, (1 - ideal_0) * decay_rate_sum
        else:
            alpha_T0, alpha_D0 = alpha_T, alpha_D
        source = N_REF / (steady_start / alpha_T0 + (1 - steady_start) / alpha_D0)   # total fuelling
        nT = steady_start * source / alpha_T0 * np.ones(n_runs)
        nD = (1 - steady_start) * source / alpha_D0 * np.ones(n_runs)
        integral_error = source / KI * np.ones(n_runs)     # the PI controller already supplies `source`
        hp_x_prev = nD * nT                                # high-pass filter at rest

    # --- bookkeeping ------------------------------------------------------------
    energy = np.zeros(n_runs); P_prev = np.zeros(n_runs)
    streak = np.zeros(n_runs, dtype=np.int64)          # consecutive in-bound samples
    streak_start = np.zeros(n_runs, dtype=np.int64)
    converged = np.zeros(n_runs, dtype=bool)
    conv_time = np.full(n_runs, np.nan)
    if return_traces:
        tr = {key: np.empty((n_steps, n_runs)) for key in ('r', 'r_hat', 'nD', 'nT', 'P', 'r_ideal')}
    if track:
        # moving average over a whole number of dither periods (closest to 1 s), one window length per run
        with np.errstate(divide='ignore', invalid='ignore'):
            periods = np.maximum(1, np.round(f * 1.0))
            window = np.where(f > 0, np.round(periods / (f * dt)), round(1.0 / dt)).astype(np.int64)
        window = np.maximum(window, 1)
        buffer_size = int(window.max()) + 1
        r_buffer = np.zeros((buffer_size, n_runs)); ideal_buffer = np.zeros((buffer_size, n_runs))
        r_sum = np.zeros(n_runs); ideal_sum = np.zeros(n_runs)
        error_sum = np.zeros(n_runs); error_late_sum = np.zeros(n_runs)
        n_error = np.zeros(n_runs); n_late = np.zeros(n_runs)
        last_above = [np.full(n_runs, -np.inf) for _ in settle_tolerances]   # last time the error was above tol
        run_index = np.arange(n_runs)

    for i in range(n_steps):
        t_now = t_vec[i]
        if drifting:
            ideal = ideal_at(t_now)
            alpha_T = ideal * decay_rate_sum
            alpha_D = (1 - ideal) * decay_rate_sum
            Ad_D, Ad_T = np.exp(-alpha_D * dt), np.exp(-alpha_T * dt)
            Bd_D, Bd_T = (1 - Ad_D) / alpha_D, (1 - Ad_T) / alpha_T

        # fuel ratio applied to the plasma
        if use_esc:
            s = np.sin(omega * t_now + dither_phase)
            r = np.fmin(np.fmax(r_hat + a * s, 0.0), 1.0)   # like MATLAB min(max(x,0),1)
            if ratio_map is not None:
                r = ratio_map(r_hat + a * s)                 # requested ratio -> ratio the plasma receives
        elif isinstance(fixed_ratio, str):                   # 'ideal': follow r_ideal(t) exactly
            r = np.broadcast_to(ideal, (n_runs,)).astype(float)
        else:
            r = np.full(n_runs, float(fixed_ratio))

        if track:
            ideal_now = np.broadcast_to(ideal, (n_runs,))
            old_slot = (i - window) % buffer_size                   # value that leaves the window
            leaving = i - window >= 0
            r_sum += r - np.where(leaving, r_buffer[old_slot, run_index], 0.0)
            ideal_sum += ideal_now - np.where(leaving, ideal_buffer[old_slot, run_index], 0.0)
            r_buffer[i % buffer_size] = r; ideal_buffer[i % buffer_size] = ideal_now
            full = i >= window - 1
            error = np.abs(r_sum - ideal_sum) / window
            error_sum += np.where(full, error, 0.0); n_error += full
            if t_now >= tend / 2:
                error_late_sum += np.where(full, error, 0.0); n_late += full
            for tol, last in zip(settle_tolerances, last_above):
                last[full & (error > tol)] = t_now

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
    if track:
        out['tracking_error'] = error_sum / n_error
        out['tracking_error_late'] = error_late_sum / n_late
        first_measured = (window - 1) * dt                    # first time with a full window (one per run)
        for tol, last in zip(settle_tolerances, last_above):
            settled = last <= tend - CONV_HOLD_TIME          # not exceeded during the last 5 s
            out[f'settling_time_{tol:g}'] = np.where(settled, np.maximum(last + dt, first_measured), np.nan)
    if return_traces:
        tr['t'] = t_vec
        out['traces'] = tr
    return out


def simulate_in_chunks(*args, chunk=20000, progress=None, **kwargs):
    """Same as simulate(), but splits large batches to limit memory use.

    progress: if a text is given, one line is printed after every chunk (text, runs done, seconds).
    """
    import time
    per_run_kw = {key: (drift_codes(val) if key == 'drift_shape' else np.asarray(val, dtype=float))
                  for key, val in kwargs.items()
                  if key in ('tau_D', 'tau_T', 'tau_scale', 'r_ideal_0', 'lambda_r_ideal', 'r_hat_0',
                             'drift_shape', 'drift_size', 'drift_time') and np.ndim(val) > 0}
    # one entry per run for every positional argument, also when only the keyword arguments are arrays
    arrs = _as_runs(*args, *per_run_kw.values())[:len(args)]
    n = arrs[0].size
    parts = []
    start_time = time.time()
    for start in range(0, n, chunk):
        sl = slice(start, start + chunk)
        kw = dict(kwargs); kw.update({key: val[sl] for key, val in per_run_kw.items()})
        parts.append(simulate(*[x[sl] for x in arrs], **kw))
        if progress:
            print(f'{progress}: {min(start + chunk, n)}/{n} runs, {time.time() - start_time:.0f} s', flush=True)
    return {key: np.concatenate([part[key] for part in parts]) for key in parts[0] if key != 'traces'}
