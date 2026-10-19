%% Prerequisites
clc; clear all; close all;

%% ESC parameters
dither_amplitude = 0.1;
dither_frequency = 0.1;
optimizer_gain   = 4e-4;

dither_omega = dither_frequency * 2 * pi;
highpass_cutoff_omega = dither_omega / pi;
lowpass_cutoff_omega  = dither_omega / pi;
initial_ratio = 0.1;

%% Settings and background calculations
% Time
tend = 100;
dt = 0.01;

% Density-related constants
n_D_decay_rate = 1/(1.71 + (rand()-0.5)*0.2); % +- 0.1
n_T_decay_rate = 1/(1.66 + (rand()-0.5)*0.2); % +- 0.1
total_density_reference = 11.5; % e19 removed for numerical stability
greenwald_density_limit = 11.9; % e19 removed for numerical stability

% Density controller
proportional_gain = 3.129;
integral_gain = 2.482;

% Ideal fuel ratio
ideal_ratio = n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate);

% Calculate transfer function of dynamics and discretize
% State-space model for densities 
n_D_dynamics = ss(-n_D_decay_rate, 1, 1, 0); % dx/dt = A*x + B*u   ;   y = C*x + D*u
n_T_dynamics = ss(-n_T_decay_rate, 1, 1, 0);

% Discretize time & Extract Ad and Bd for simulating
n_D_dynamics_discretized = c2d(n_D_dynamics, dt); % Ts = dt
n_T_dynamics_discretized = c2d(n_T_dynamics, dt); % nT[k] = Ad_T*nT[k-1] + Bd_T*uT[k-1]
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


%% States
initial_nD = 0.25 * (1-initial_ratio) * total_density_reference;
initial_nT = 0.25 * initial_ratio * total_density_reference;

nD = initial_nD;
nT = initial_nT;
r_hat = 0;
integral_density_error = 0;

t_vec = (0:dt:tend)'; % create a time vector
n_steps = length(t_vec);
P_vec = nan(n_steps,1);
r_vec = nan(n_steps,1);
r_hat_vec = nan(n_steps,1);
nD_vec = nan(n_steps,1); % for plotting
nT_vec = nan(n_steps,1); % for plotting

%% Live plotting
figure('Position',[100 100 1300 650]);
tiledlayout(3, 3);

% n_D + n_T
nexttile(1); hold on; box on;
h_sum = plot(nan, nan, 'b-');
yline(total_density_reference, 'c--');
yline(greenwald_density_limit, 'r--');
ylabel('$n_D + n_T$', 'Interpreter','latex');
xlim([0 tend]);
legend("$n_D + n_T$", "$n_D + n_T$ reference", "greenwald density", 'Interpreter','latex', 'Location','southeast');

% n_T
nexttile(4); hold on; box on;
h_nT = plot(nan, nan, 'b-');
h_nT_ref = plot(nan, nan, 'c--');
ylabel('$n_T$', 'Interpreter','latex');
xlim([0 tend]);
legend("$n_T$", "$n_T$ reference", 'Interpreter','latex', 'Location','southeast');

% n_D
nexttile(7); hold on; box on;
h_nD = plot(nan, nan, 'b-');
h_nD_ref = plot(nan, nan, 'c--');
ylabel('$n_D$', 'Interpreter','latex');
xlabel('$t$ [s]', 'Interpreter','latex');
xlim([0 tend]);
legend("$n_D$", "$n_D$ reference", 'Interpreter','latex', 'Location','southeast');

% n_D * n_T
nexttile(2); hold on; box on;
h_P = plot(nan, nan, 'b-');
yline(0.25 * total_density_reference^2, 'c--');
ylabel('$n_D \times n_T$', 'Interpreter','latex');
xlim([0 tend]);
legend("$n_D \times n_T$", "ideal $n_D \times n_T$", 'Interpreter','latex', 'Location','southeast');

% r
nexttile(5); hold on; box on;
h_r = plot(nan, nan, 'b-');
yline(ideal_ratio, 'c--');
ylabel('$r$', 'Interpreter','latex');
xlim([0 tend]);
legend("current ratio", "ideal ratio", 'Interpreter','latex', 'Location','southeast');

% r_hat
nexttile(8); hold on; box on;
h_rhat = plot(nan, nan, 'b-');
yline(ideal_ratio, 'c--');
ylabel('$\hat{r}$', 'Interpreter','latex');
xlabel('$t$ [s]', 'Interpreter','latex');
xlim([0 tend]);
legend("nominal ratio", "ideal ratio", 'Interpreter','latex', 'Location','southeast');

% n_D * n_T vs r_hat
nexttile(3, [3 1]); hold on; box on;
h_P_rhat = plot(nan, nan, 'b-');
xline(ideal_ratio, 'c--');
yline(0.25 * total_density_reference^2, 'c:');
xlabel('$\hat{r}$', 'Interpreter','latex');
ylabel('$n_D \times n_T$', 'Interpreter','latex');
legend("$n_D \times n_T$", "ideal ratio", "ideal $n_D \times n_T$", 'Interpreter','latex', 'Location','southeast');

plot_update_every = 50;  % update the figure every N steps (for speed)

%% Automated ESC loop
for k = 1:n_steps
    % Set current time
    t_now = t_vec(k);
    
    % Current r
    r = r_hat + dither_amplitude * sin(dither_omega * t_now); 
    r = min(max(r, 0), 1); % 0 <= r <= 1

    % Error computation
    e_density = total_density_reference - (nD + nT); % how far off right now
    integral_density_error = integral_density_error + e_density * dt; % how far off historically
    S_total = proportional_gain * e_density + integral_gain * integral_density_error;
    S_total = max(S_total, 0);

    % Fuel pumping & Update densities
    u_T = r * S_total;
    u_D = (1 - r) * S_total;
    nD = Ad_D * nD + Bd_D * u_D;
    nT = Ad_T * nT + Bd_T * u_T;

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
    P_vec(k) = P;
    r_vec(k) = r;
    r_hat_vec(k) = r_hat;
    nD_vec(k) = nD;
    nT_vec(k) = nT;

    if mod(k, plot_update_every) == 0 || k == n_steps
        tk = t_vec(1:k);
        set(h_sum,    'XData', tk, 'YData', nD_vec(1:k) + nT_vec(1:k));
        set(h_nT,     'XData', tk, 'YData', nT_vec(1:k));
        set(h_nT_ref, 'XData', tk, 'YData', r_vec(1:k) * total_density_reference);
        set(h_nD,     'XData', tk, 'YData', nD_vec(1:k));
        set(h_nD_ref, 'XData', tk, 'YData', (1 - r_vec(1:k)) * total_density_reference);
        set(h_P,      'XData', tk, 'YData', P_vec(1:k));
        set(h_r,      'XData', tk, 'YData', r_vec(1:k));
        set(h_rhat,   'XData', tk, 'YData', r_hat_vec(1:k));
        set(h_P_rhat, 'XData', r_hat_vec(1:k), 'YData', P_vec(1:k));
        drawnow;
    end
end

fprintf('Final r_hat = %.4f, ideal ratio = %.4f\n', r_hat, ideal_ratio);
