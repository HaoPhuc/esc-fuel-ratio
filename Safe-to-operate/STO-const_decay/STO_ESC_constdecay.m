%% Prerequisites
clc; clear all; close all;

%% Create table and preallocate results
results = table(Size = [0 5], ...
    VariableTypes = {'double','double','double','logical','double'}, ...
    VariableNames = {'optimizer_gain','dither_amplitude','dither_frequency','converged','convergence_time'});
%% Batch sweep settings
combinations = 200000; % total random sets to test
save_every = 5000; % add results to CSV every N combinations
csv_filename = 'STO-const_decay-200k.csv';

%% Simulation settings
% Time
tend = 100;
dt = 0.01;

% Convergence
convergence_fraction = 0.05; % r_hat within 5% of ideal_ratio
conv_hold_time = 5; % must stay within bound

%% Batch loop
for i = 1:combinations

    % ESC parameters range
    optimizer_gain_range   = [1e-5, 5];
    dither_amplitude_range = [1e-708, 1];
    dither_frequency_range = [1e-708, 10];    
    
    % ESC parameters (randomized)
    dither_amplitude = dither_amplitude_range(1) + diff(dither_amplitude_range) * rand();
    dither_frequency = dither_frequency_range(1) + diff(dither_frequency_range) * rand();
    log_range = log10(optimizer_gain_range);
    optimizer_gain = 10^(log_range(1) + diff(log_range) * rand()); %randomize the power

    % Run trial
    [converged, convergence_time] = esc_trial(dither_amplitude, dither_frequency, optimizer_gain, dt, tend, convergence_fraction, conv_hold_time);

    % Append results
    results = [results; {optimizer_gain, dither_amplitude, dither_frequency, converged, convergence_time}];

    % Print progress to the console
    fprintf('Trial %d/%d: gain=%.4g, amp=%.4g, freq=%.4g -> converged=%d, conv_time=%.2f\n', i, combinations, optimizer_gain, dither_amplitude, dither_frequency, converged, convergence_time);

    % Save progress to csv every N combinations (just in case)
    if mod(i, save_every) == 0 || i == combinations
        writetable(results, csv_filename); % overwrite each time
    end
end

disp('Batch sweep complete');


%% Run one ESC trial & Convergence check

% ESC TRIAL (same as in ESC.m)

function [converged, convergence_time] = esc_trial(dither_amplitude, dither_frequency, optimizer_gain, dt, tend, fraction, hold_time)

    dither_omega = dither_frequency * 2 * pi;
    highpass_cutoff_omega = dither_omega / pi;
    lowpass_cutoff_omega  = dither_omega / pi;
    initial_ratio = 0.1;

    % Density-related constants
    n_D_decay_rate = 1/1.71; 
    n_T_decay_rate = 1/1.66;
    total_density_reference = 11.5; % e19 removed for numerical stability

    % Density controller
    proportional_gain = 3.129;
    integral_gain = 2.482;

    % Ideal fuel ratio
    ideal_ratio = n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate);
    % State-space model for densities 
    n_D_dynamics = ss(-n_D_decay_rate, 1, 1, 0); % dx/dt = A*x + B*u   ;   y = C*x + D*u
    n_T_dynamics = ss(-n_T_decay_rate, 1, 1, 0);

    % Discretize time & Extract Ad and Bd for simulating
    n_D_dynamics_discretized = c2d(n_D_dynamics, dt); % Ts = dt
    n_T_dynamics_discretized = c2d(n_T_dynamics, dt);
    [Ad_D, Bd_D, ~, ~] = ssdata(n_D_dynamics_discretized);
    [Ad_T, Bd_T, ~, ~] = ssdata(n_T_dynamics_discretized);

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
    r_hat = 0;
    integral_density_error = 0;

    % Loop setting
    t_vec = (0:dt:tend)';
    n_steps = length(t_vec);
    r_hat_vec = nan(n_steps,1);

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
        nD = Ad_D*nD + Bd_D*u_D;
        nT = Ad_T*nT + Bd_T*u_T;

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
    end

   
    
% CONVERGENCE CHECK

    % Convergence condition
    bound_range = fraction * ideal_ratio;
    in_bound = abs(r_hat_vec - ideal_ratio) <= bound_range; % boolean list
    
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