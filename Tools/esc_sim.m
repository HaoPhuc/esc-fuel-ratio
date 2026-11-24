function out = esc_sim(optimizer_gain, dither_amplitude, dither_frequency, varargin)
%ESC_SIM  Simulate many ESC fuel-ratio runs at once (MATLAB version of Tools/esc_sim.py).
%
%   out = esc_sim(k, a, f, 'Name', value, ...)
%
%   Follows esc_sim.py step for step, so MATLAB and Python give the same numbers (to rounding).
%   k (optimizer gain), a (dither amplitude) and f (dither frequency [Hz]) are scalars or vectors
%   of equal length; one element per run. Every run gets its own row in the output.
%
%   Model (same symbols as the MATLAB scripts)
%       dn_D/dt = -alpha_D n_D + (1 - r) S        dn_T/dt = -alpha_T n_T + r S
%       S = max(0, Kp e + Ki int(e)),  e = n_ref - (n_D + n_T)        (PI density control)
%       r = clip(r_hat + a sin(w t), 0, 1)                              (dither)
%       P = n_D n_T -> high-pass s/(s+w/pi) -> x (2/a) sin(w t) -> low-pass (w/pi)/(s+w/pi) -> xi
%       dr_hat/dt = k xi                                                (integrator)
%   All blocks are discretised with a zero-order hold at dt, as in the MATLAB sweep scripts.
%
%   Plant, two modes
%     constant plant (default)  'TauD', 'TauT'  confinement times [s] (scalars or one per run);
%                               r_ideal = alpha_T / (alpha_T + alpha_D)
%     drifting plant            'RIdeal0' (and 'LambdaRIdeal' [1/s]):
%                               r_ideal(t) = r_ideal_0 exp(lambda t), alpha_T = r_ideal A,
%                               alpha_D = (1 - r_ideal) A, A = 1/1.71 + 1/1.66
%   Controller
%     'RHat0'        (0)     start value of r_hat (scalar or one per run)
%     'UseESC'       (true)  false: the ratio is held at 'FixedRatio' (no dither, no optimiser)
%     'FixedRatio'   (0.5)   a number, or 'ideal' to follow r_ideal(t) exactly
%   Options of the newer sweeps (the defaults reproduce the original MATLAB scripts)
%     'DitherPhase'  (0)     dither and demodulation use sin(w t + phase); pi: first swing downwards
%     'InitialRatio' (0.1)   tritium fraction of the initial densities (25 % density start)
%     'MirrorPlant'  (false) drifting plant only: use 1 - r_ideal_0 exp(lambda t)
%     'SteadyStart'  ([])    e.g. 0.5: start from a plasma already running at that ratio (full
%                            density, steady state, controller and high-pass filter at rest)
%     'RatioMap'     ([])    function handle: requested ratio -> ratio the plasma receives
%                            (default: clipping to [0, 1])
%     'Track'        (false) also compute tracking_error, tracking_error_late and settling_time,
%                            from the received ratio averaged over a whole number of dither periods
%     'SettleTolerances' ([0.01 0.02])
%     'Dt' (0.01), 'Tend' (100)   time step and run length [s]
%     'Chunk'        (20000) runs simulated at once (limits the memory use)
%     'Progress'     ('')    if a text is given, one line is printed after every chunk
%
%   Output: struct of column vectors (one entry per run)
%     converged, convergence_time [s] (NaN if not converged), energy (= int n_D n_T dt),
%     r_hat_final, ideal_ratio (final value for a drifting plant),
%     and with 'Track': tracking_error, tracking_error_late, settling_time (runs x tolerances,
%     NaN if the tolerance is exceeded during the last 5 s), settle_tolerances.
%
%   Example
%     out = esc_sim(1, 0.2, 6, 'RIdeal0', 0.525, 'RHat0', 0.5, 'SteadyStart', 0.5, 'Track', true);
%
%   See also ESC_RNG, ESC_DRAW, ESC_WRITE_CSV, VALIDATE_MATLAB_PORTS.

p = inputParser;
p.FunctionName = 'esc_sim';
addParameter(p, 'TauD', 1.71);
addParameter(p, 'TauT', 1.66);
addParameter(p, 'RIdeal0', []);
addParameter(p, 'LambdaRIdeal', 0);
addParameter(p, 'RHat0', 0);
addParameter(p, 'UseESC', true);
addParameter(p, 'FixedRatio', 0.5);
addParameter(p, 'DitherPhase', 0);
addParameter(p, 'InitialRatio', 0.1);
addParameter(p, 'MirrorPlant', false);
addParameter(p, 'SteadyStart', []);
addParameter(p, 'RatioMap', []);
addParameter(p, 'Track', false);
addParameter(p, 'SettleTolerances', [0.01 0.02]);
addParameter(p, 'Dt', 0.01);
addParameter(p, 'Tend', 100);
addParameter(p, 'Chunk', 20000);
addParameter(p, 'Progress', '');
parse(p, varargin{:});
opt = p.Results;

% one entry per run for every input (scalars are repeated)
drifting = ~isempty(opt.RIdeal0);
if drifting
    per_run = {optimizer_gain, dither_amplitude, dither_frequency, opt.RIdeal0, opt.LambdaRIdeal, opt.RHat0};
else
    per_run = {optimizer_gain, dither_amplitude, dither_frequency, opt.TauD, opt.TauT, opt.RHat0};
end
n = max(cellfun(@numel, per_run));
for j = 1:numel(per_run)
    x = double(per_run{j}(:));
    if numel(x) == 1
        x = repmat(x, n, 1);
    elseif numel(x) ~= n
        error('esc_sim:size', 'All per-run inputs must be scalars or have the same length (%d).', n);
    end
    per_run{j} = x;
end

% simulate in chunks and join the results
parts = {};
t_start = tic;
for first = 1:opt.Chunk:n
    rows = first:min(first + opt.Chunk - 1, n);
    sliced = cellfun(@(x) x(rows), per_run, 'UniformOutput', false);
    parts{end + 1} = simulate_chunk(sliced, drifting, opt); %#ok<AGROW>
    if ~isempty(opt.Progress)
        fprintf('%s: %d/%d runs, %.0f s\n', opt.Progress, rows(end), n, toc(t_start));
    end
end
out = parts{1};
names = fieldnames(out);
for j = 2:numel(parts)
    for q = 1:numel(names)
        if ~strcmp(names{q}, 'settle_tolerances')
            out.(names{q}) = [out.(names{q}); parts{j}.(names{q})];
        end
    end
end
end


function out = simulate_chunk(per_run, drifting, opt)
% One batch of runs. Line by line the same as simulate() in esc_sim.py.

% ---- constants shared by every script in the repository (as in esc_sim.py) ----------
N_REF = 11.5;                         % total density reference [1e19 m^-3]
KP = 3.129; KI = 2.482;               % PI gains of the total-density controller
CONV_FRACTION = 0.05;                 % r_hat must be within 5 % of r_ideal ...
CONV_HOLD_TIME = 5.0;                 % ... for 5 s to count as converged
DECAY_RATE_SUM = 1 / 1.71 + 1 / 1.66; % kept constant in the drifting plant

k = per_run{1}; a = per_run{2}; f = per_run{3}; rh0 = per_run{6};
if drifting
    r0 = per_run{4}; lam = per_run{5};
else
    tD = per_run{4}; tT = per_run{5};
end
n_runs = numel(k);
dt = opt.Dt; tend = opt.Tend;
n_steps = round(tend / dt) + 1;
hold_steps = round(CONV_HOLD_TIME / dt);

% ---- plant (zero-order hold: x[k+1] = Ad x[k] + Bd u[k]) ------------------------------
if ~drifting
    alpha_D = 1 ./ tD; alpha_T = 1 ./ tT;
    ideal = alpha_T ./ (alpha_T + alpha_D);
    Ad_D = exp(-alpha_D * dt); Ad_T = exp(-alpha_T * dt);
    Bd_D = (1 - Ad_D) ./ alpha_D; Bd_T = (1 - Ad_T) ./ alpha_T;
end

% ---- ESC filters (zero-order hold of s/(s+wc) and wc/(s+wc), wc = w/pi) ---------------
omega = 2 * pi * f;
p = exp(-(omega / pi) * dt);          % pole of both discrete filters
hp_x_prev = zeros(n_runs, 1); hp_y_prev = zeros(n_runs, 1);   % high-pass memory
lp_x_prev = zeros(n_runs, 1); lp_y_prev = zeros(n_runs, 1);   % low-pass memory
demod_gain = 2 ./ a;

% ---- states --------------------------------------------------------------------------
nD = repmat(0.25 * (1 - opt.InitialRatio) * N_REF, n_runs, 1);
nT = repmat(0.25 * opt.InitialRatio * N_REF, n_runs, 1);
r_hat = rh0;
integral_error = zeros(n_runs, 1);
if ~isempty(opt.SteadyStart)
    % plasma already running at the ratio SteadyStart: total density n_ref, nothing changes in time
    if drifting
        ideal_0 = r0;
        if opt.MirrorPlant
            ideal_0 = 1.0 - r0;
        end
        alpha_T0 = ideal_0 * DECAY_RATE_SUM; alpha_D0 = (1 - ideal_0) * DECAY_RATE_SUM;
    else
        alpha_T0 = alpha_T; alpha_D0 = alpha_D;
    end
    ss = opt.SteadyStart;
    source = N_REF ./ (ss ./ alpha_T0 + (1 - ss) ./ alpha_D0);       % total fuelling
    nT = ss * source ./ alpha_T0;
    nD = (1 - ss) * source ./ alpha_D0;
    integral_error = source / KI;     % the PI controller already supplies `source`
    hp_x_prev = nD .* nT;             % high-pass filter at rest
end
follow_ideal = ischar(opt.FixedRatio) || isstring(opt.FixedRatio);

% ---- bookkeeping ---------------------------------------------------------------------
energy = zeros(n_runs, 1); P_prev = zeros(n_runs, 1);
streak = zeros(n_runs, 1);            % consecutive in-bound samples
streak_start = zeros(n_runs, 1);
converged = false(n_runs, 1);
conv_time = nan(n_runs, 1);
if opt.Track
    % moving average over a whole number of dither periods (closest to 1 s), one window per run
    periods = max(1, round_half_even(f * 1.0));
    window = round_half_even(periods ./ (f * dt));
    window(~(f > 0)) = round_half_even(1.0 / dt);
    window = max(window, 1);
    buffer_size = max(window) + 1;
    r_buffer = zeros(n_runs, buffer_size); ideal_buffer = zeros(n_runs, buffer_size);   % one column per time slot
    r_sum = zeros(n_runs, 1); ideal_sum = zeros(n_runs, 1);
    error_sum = zeros(n_runs, 1); error_late_sum = zeros(n_runs, 1);
    n_error = zeros(n_runs, 1); n_late = zeros(n_runs, 1);
    tols = opt.SettleTolerances(:)';
    last_above = -inf(n_runs, numel(tols));   % last time the error was above the tolerance
    run_index = (1:n_runs)';
end

for step = 1:n_steps
    i = step - 1;                     % 0-based step number, as in Python
    t_now = i * dt;
    if drifting
        ideal = r0 .* exp(lam * t_now);
        if opt.MirrorPlant
            ideal = 1.0 - ideal;
        end
        alpha_T = ideal * DECAY_RATE_SUM;
        alpha_D = (1 - ideal) * DECAY_RATE_SUM;
        Ad_D = exp(-alpha_D * dt); Ad_T = exp(-alpha_T * dt);
        Bd_D = (1 - Ad_D) ./ alpha_D; Bd_T = (1 - Ad_T) ./ alpha_T;
    end

    % fuel ratio applied to the plasma
    if opt.UseESC
        s = sin(omega * t_now + opt.DitherPhase);
        if isempty(opt.RatioMap)
            r = min(max(r_hat + a .* s, 0.0), 1.0);
        else
            r = opt.RatioMap(r_hat + a .* s);      % requested ratio -> ratio the plasma receives
        end
    elseif follow_ideal                            % follow r_ideal(t) exactly
        r = ideal .* ones(n_runs, 1);
    else
        r = repmat(opt.FixedRatio, n_runs, 1);
    end

    if opt.Track
        ideal_now = ideal .* ones(n_runs, 1);
        old_slot = mod(i - window, buffer_size) + 1;            % value that leaves the window
        leaving = (i - window) >= 0;
        old = sub2ind([n_runs, buffer_size], run_index, old_slot);
        r_leaving = r_buffer(old); r_leaving(~leaving) = 0;
        ideal_leaving = ideal_buffer(old); ideal_leaving(~leaving) = 0;
        r_sum = r_sum + (r - r_leaving);
        ideal_sum = ideal_sum + (ideal_now - ideal_leaving);
        slot = mod(i, buffer_size) + 1;
        r_buffer(:, slot) = r; ideal_buffer(:, slot) = ideal_now;
        full = i >= window - 1;
        err = abs(r_sum - ideal_sum) ./ window;
        error_sum(full) = error_sum(full) + err(full); n_error = n_error + full;
        if t_now >= tend / 2
            error_late_sum(full) = error_late_sum(full) + err(full); n_late = n_late + full;
        end
        for j = 1:numel(tols)
            last_above(full & (err > tols(j)), j) = t_now;
        end
    end

    % PI controller on the total density
    e = N_REF - (nD + nT);
    integral_error = integral_error + e * dt;
    S_total = max(KP * e + KI * integral_error, 0.0);

    % fuelling (r is the TRITIUM fraction of the puff) and density update
    u_T = r .* S_total;
    u_D = (1 - r) .* S_total;
    nD = Ad_D .* nD + Bd_D .* u_D;
    nT = Ad_T .* nT + Bd_T .* u_T;
    P = nD .* nT;

    if opt.UseESC
        % high-pass: y[n] = x[n] - x[n-1] + p y[n-1]
        hp = P - hp_x_prev + p .* hp_y_prev;
        hp_x_prev = P; hp_y_prev = hp;
        demod = hp .* demod_gain .* s;
        % low-pass: y[n] = (1-p) x[n-1] + p y[n-1]
        xi = (1 - p) .* lp_x_prev + p .* lp_y_prev;
        lp_x_prev = demod; lp_y_prev = xi;
        % integrator k/s
        r_hat = min(max(r_hat + k .* xi * dt, 0.0), 1.0);

        % convergence: first streak of hold_steps samples inside the 5 % band
        in_bound = abs(r_hat - ideal) <= CONV_FRACTION * ideal;
        streak_start(in_bound & (streak == 0)) = i;
        streak(in_bound) = streak(in_bound) + 1;
        streak(~in_bound) = 0;
        newly = ~converged & (streak >= hold_steps);
        conv_time(newly) = streak_start(newly) * dt;
        converged = converged | newly;
    end

    % energy = trapz(t, P)
    if i > 0
        energy = energy + 0.5 * (P + P_prev) * dt;
    end
    P_prev = P;
end

out.converged = converged;
out.convergence_time = conv_time;
out.energy = energy;
out.r_hat_final = r_hat;
out.ideal_ratio = ideal .* ones(n_runs, 1);
if opt.Track
    out.tracking_error = error_sum ./ n_error;
    out.tracking_error_late = error_late_sum ./ n_late;
    first_measured = (window - 1) * dt;          % first time with a full window (one per run)
    settled = last_above <= tend - CONV_HOLD_TIME; % not exceeded during the last 5 s
    settling = max(last_above + dt, first_measured);
    settling(~settled) = NaN;
    out.settling_time = settling;
    out.settle_tolerances = tols;
end
end


function y = round_half_even(x)
% Round to the nearest integer, halves to the even neighbour (like numpy.round).
y = round(x);
tie = abs(x - fix(x)) == 0.5;
y(tie) = 2 * round(x(tie) / 2);
end
