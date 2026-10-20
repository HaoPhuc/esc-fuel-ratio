%% Prerequisites
clc; clear all; close all;

%% Create table and preallocate results
results = table(Size = [0 11], ...
    VariableTypes = {'double','double','double','double','double','double','double','double','double','logical','double'}, ...
    VariableNames = {'optimizer_gain','dither_amplitude','dither_frequency','r_ideal_0','lambda_r_ideal', ...
                     'energy_ESC','energy_const','energy_max','choose_ESC','converged','convergence_time'});
%% Batch sweep settings
combinations = 200000; % total random sets to test
save_every = 5000; % add results to CSV every N combinations
csv_filename = 'OTO-ESC-200k.csv';

%% Simulation settings
% Time
tend = 100;
dt = 0.01;

% Convergence
convergence_fraction = 0.05; % r_hat within 5% of r_ideal(t)
conv_hold_time = 5; % must stay within bound

% Fuel ratio
r_hat_0 = 0.5;     % ESC starting fuel ratio
const_ratio = 0.5; % fixed fuel ratio without ESC

% Theoretical maximum energy: n_D = n_T = n_ref/2 the whole time (same for every case)
total_density_reference = 11.5; % e19 removed for numerical stability
energy_max = 0.25 * total_density_reference^2 * tend;

%% Batch loop
for i = 1:combinations

    % ESC parameters range
    optimizer_gain_range   = [1e-5, 5];
    dither_amplitude_range = [1e-708, 1];
    dither_frequency_range = [1e-708, 10];

    % Ideal fuel ratio range: r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t)
    r_ideal_0_range      = [0.45, 0.55];
    lambda_r_ideal_range = [-0.002, 0.002]; % 1/s

    % ESC parameters (randomized)
    dither_amplitude = dither_amplitude_range(1) + diff(dither_amplitude_range) * rand();
    dither_frequency = dither_frequency_range(1) + diff(dither_frequency_range) * rand();
    log_range = log10(optimizer_gain_range);
    optimizer_gain = 10^(log_range(1) + diff(log_range) * rand()); %randomize the power

    % Ideal fuel ratio (randomized)
    r_ideal_0      = r_ideal_0_range(1) + diff(r_ideal_0_range) * rand();
    lambda_r_ideal = lambda_r_ideal_range(1) + diff(lambda_r_ideal_range) * rand();

    % Run trials
    [converged, convergence_time, energy_ESC] = esc_trial(dither_amplitude, dither_frequency, optimizer_gain, r_hat_0, r_ideal_0, lambda_r_ideal, dt, tend, convergence_fraction, conv_hold_time);
    energy_const = fixed_ratio_trial(const_ratio, r_ideal_0, lambda_r_ideal, dt, tend);

    % Should we choose ESC? (1 = ESC gives more energy than the fixed ratio)
    choose_ESC = double(energy_ESC > energy_const);

    % Append results
    results = [results; {optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, ...
                         energy_ESC, energy_const, energy_max, choose_ESC, converged, convergence_time}];

    % Print progress to the console
    fprintf('Trial %d/%d: gain=%.4g, amp=%.4g, freq=%.4g, r_ideal_0=%.3f, lambda=%.4g -> E_ESC=%.1f, E_const=%.1f, choose_ESC=%d, converged=%d, conv_time=%.2f\n', ...
        i, combinations, optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, energy_ESC, energy_const, choose_ESC, converged, convergence_time);

    % Save progress to csv every N combinations (just in case)
    if mod(i, save_every) == 0 || i == combinations
        writetable(results, csv_filename); % overwrite each time
    end
end

disp('Batch sweep complete');


%% Run one ESC trial & Convergence check

% ESC TRIAL (same as in ESC_energy.m)

function [converged, convergence_time, energy] = esc_trial(dither_amplitude, dither_frequency, optimizer_gain, r_hat_0, r_ideal_0, lambda_r_ideal, dt, tend, fraction, hold_time)

    dither_omega = dither_frequency * 2 * pi;
    highpass_cutoff_omega = dither_omega / pi;
    lowpass_cutoff_omega  = dither_omega / pi;
    initial_ratio = 0.1;

    % Density-related constants
    total_density_reference = 11.5; % e19 removed for numerical stability

    % Density controller
    proportional_gain = 3.129;
    integral_gain = 2.482;

    % Time
    t_vec = (0:dt:tend)';
    n_steps = length(t_vec);

    % Plant with time-varying ideal fuel ratio
    [r_ideal_vec, Ad_D_vec, Bd_D_vec, Ad_T_vec, Bd_T_vec] = plant_discretization(r_ideal_0, lambda_r_ideal, t_vec, dt);

    % Calculate transfer functions of extremum seeking control and discretize
    highpass_filter = tf([1, 0], [1, highpass_cutoff_omega]); % H_hp(s) = s / (s + ω_hp)
    highpass_filter_discretized = c2d(highpass_filter, dt);
    lowpass_filter = tf(lowpass_cutoff_omega, [1, lowpass_cutoff_omega]); % H_lp(s) = ω_lp / (s + ω_lp)
    lowpass_filter_discretized = c2d(lowpass_filter, dt);

    % Extract usable coefficients
    [num_hp, den_hp] = tfdata(highpass_filter_discretized, 'v'); % returns row vectors rather than cell arrays for a SISO
    [num_lp, den_lp] = tfdata(lowpass_filter_discretized, 'v');

    % Initialize filter memory
    zi_hp = zeros(max(length(num_hp),length(den_hp))-1,1);
    zi_lp = zeros(max(length(num_lp),length(den_lp))-1,1);

    % States
    initial_nD = 0.25 * (1-initial_ratio) * total_density_reference;
    initial_nT = 0.25 * initial_ratio * total_density_reference;
    nD = initial_nD;
    nT = initial_nT;
    r_hat = r_hat_0;
    integral_density_error = 0;

    % Loop setting
    r_hat_vec = nan(n_steps,1);
    P_vec = nan(n_steps,1);

    for k = 1:n_steps
        % Set current time
        t_now = t_vec(k);

        % Current r
        r = r_hat + dither_amplitude * sin(dither_omega * t_now);
        r = min(max(r, 0), 1); % 0 <= r <= 1

        % Error computation
        e_density = total_density_reference - (nD + nT);
        integral_density_error = integral_density_error + e_density * dt;
        S_total = proportional_gain*e_density + integral_gain*integral_density_error;
        S_total = max(S_total, 0);

        % Fuel pumping & Update densities
        u_T = r * S_total;
        u_D = (1 - r) * S_total;
        nD = Ad_D_vec(k)*nD + Bd_D_vec(k)*u_D;
        nT = Ad_T_vec(k)*nT + Bd_T_vec(k)*u_T;

        % Rescaled P (does not matter much because we focus more on the product of densities)
        P = nD * nT;

        % Filters
        [hp_out, zi_hp] = filter(num_hp, den_hp, P, zi_hp); % high-pass filter: s / (s + ω_hp)
        demod = hp_out * (2/dither_amplitude) * sin(dither_omega * t_now); % demodulation: (2/a) * sin(ωt)
        [xi, zi_lp] = filter(num_lp, den_lp, demod, zi_lp); % low-pass filter: ω_lp / (s + ω_lp)

        % Integrator (k/s)
        r_hat = r_hat + optimizer_gain * xi * dt;
        r_hat = min(max(r_hat, 0), 1);

        % Update vectors
        r_hat_vec(k) = r_hat;
        P_vec(k) = P;
    end

    % ENERGY (fusion power ~ nD*nT, so energy ~ integral of nD*nT over time)
    energy = trapz(t_vec, P_vec);

% CONVERGENCE CHECK

    % Convergence condition (against the time-varying ideal ratio)
    bound_range = fraction * r_ideal_vec;
    in_bound = abs(r_hat_vec - r_ideal_vec) <= bound_range; % boolean list

    % Convergence time counting setting
    hold = round(hold_time / dt);
    converged = false;
    consecutive_count = 0;
    run_start_idx = 0; % index where the current in-bound streak began
    convergence_time = NaN; % default if never converged

    for b = 1:length(in_bound)
        % Counting
        if in_bound(b) == true
            if consecutive_count == 0
                run_start_idx = b; % mark the start of a fresh streak
            end
            consecutive_count = consecutive_count + 1;
        else
            consecutive_count = 0;
        end

        % Counting threshold
        if consecutive_count >= hold
            converged = true;
            convergence_time = t_vec(run_start_idx); % time the streak began
            break   % found a long enough run, no need to keep checking
        end
    end


end


%% Fixed fuel ratio trial (no ESC, same plant and density controller)

function energy = fixed_ratio_trial(r_fixed, r_ideal_0, lambda_r_ideal, dt, tend)

    initial_ratio = 0.1;

    % Density-related constants
    total_density_reference = 11.5; % e19 removed for numerical stability

    % Density controller
    proportional_gain = 3.129;
    integral_gain = 2.482;

    % Time
    t_vec = (0:dt:tend)';
    n_steps = length(t_vec);

    % Plant with time-varying ideal fuel ratio
    [~, Ad_D_vec, Bd_D_vec, Ad_T_vec, Bd_T_vec] = plant_discretization(r_ideal_0, lambda_r_ideal, t_vec, dt);

    % States (same starting point as the ESC trial)
    nD = 0.25 * (1-initial_ratio) * total_density_reference;
    nT = 0.25 * initial_ratio * total_density_reference;
    integral_density_error = 0;

    P_vec = nan(n_steps,1);

    for k = 1:n_steps
        r = r_fixed; % no dither, no optimizer

        % Error computation
        e_density = total_density_reference - (nD + nT);
        integral_density_error = integral_density_error + e_density * dt;
        S_total = proportional_gain*e_density + integral_gain*integral_density_error;
        S_total = max(S_total, 0);

        % Fuel pumping & Update densities
        u_T = r * S_total;
        u_D = (1 - r) * S_total;
        nD = Ad_D_vec(k)*nD + Bd_D_vec(k)*u_D;
        nT = Ad_T_vec(k)*nT + Bd_T_vec(k)*u_T;

        P_vec(k) = nD * nT;
    end

    energy = trapz(t_vec, P_vec);
end


%% Plant with time-varying ideal fuel ratio (used by both trials)

function [r_ideal_vec, Ad_D_vec, Bd_D_vec, Ad_T_vec, Bd_T_vec] = plant_discretization(r_ideal_0, lambda_r_ideal, t_vec, dt)

    % Ideal fuel ratio: r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t)
    r_ideal_vec = r_ideal_0 * exp(lambda_r_ideal * t_vec);

    % Decay rates: their sum is kept constant, their split gives
    % n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate) = r_ideal(t)
    decay_rate_sum = 1/1.71 + 1/1.66;
    n_T_decay_rate_vec = r_ideal_vec * decay_rate_sum;
    n_D_decay_rate_vec = (1 - r_ideal_vec) * decay_rate_sum;

    % Discretize dx/dt = -decay_rate*x + u at every time step
    % (zero-order hold, same as c2d(ss(-decay_rate,1,1,0), dt))
    Ad_D_vec = exp(-n_D_decay_rate_vec * dt);
    Bd_D_vec = (1 - Ad_D_vec) ./ n_D_decay_rate_vec;
    Ad_T_vec = exp(-n_T_decay_rate_vec * dt);
    Bd_T_vec = (1 - Ad_T_vec) ./ n_T_decay_rate_vec;
end
