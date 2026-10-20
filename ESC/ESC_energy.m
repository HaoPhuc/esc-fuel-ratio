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
r_hat_0 = 0.5; % ESC starting fuel ratio

%% Settings and background calculations
% Time
tend = 100;
dt = 0.01;
t_vec = (0:dt:tend)'; % create a time vector
n_steps = length(t_vec);

% Ideal fuel ratio: r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t)
r_ideal_0_range      = [0.45, 0.55];
lambda_r_ideal_range = [-0.002, 0.002]; % 1/s
r_ideal_0      = r_ideal_0_range(1) + diff(r_ideal_0_range) * rand();
lambda_r_ideal = lambda_r_ideal_range(1) + diff(lambda_r_ideal_range) * rand();
r_ideal_vec = r_ideal_0 * exp(lambda_r_ideal * t_vec);

% Density-related constants
% Decay rates: their sum is kept constant, their split gives
% n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate) = r_ideal(t)
decay_rate_sum = 1/1.71 + 1/1.66;
n_T_decay_rate_vec = r_ideal_vec * decay_rate_sum;
n_D_decay_rate_vec = (1 - r_ideal_vec) * decay_rate_sum;
total_density_reference = 11.5; % e19 removed for numerical stability
greenwald_density_limit = 11.9; % e19 removed for numerical stability

% Density controller
proportional_gain = 3.129;
integral_gain = 2.482;

% Discretize dx/dt = -decay_rate*x + u at every time step
% (zero-order hold, same as c2d(ss(-decay_rate,1,1,0), dt))
% nT[k+1] = Ad_T(k)*nT[k] + Bd_T(k)*u_T[k]
Ad_D_vec = exp(-n_D_decay_rate_vec * dt);
Bd_D_vec = (1 - Ad_D_vec) ./ n_D_decay_rate_vec;
Ad_T_vec = exp(-n_T_decay_rate_vec * dt);
Bd_T_vec = (1 - Ad_T_vec) ./ n_T_decay_rate_vec;

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

% Ideal case (theoretical maximum): n_D = n_T = n_ref/2 the whole time
energy_max_vec = 0.25 * total_density_reference^2 * t_vec;


%% States
initial_nD = 0.25 * (1-initial_ratio) * total_density_reference;
initial_nT = 0.25 * initial_ratio * total_density_reference;

nD = initial_nD;
nT = initial_nT;
r_hat = r_hat_0;
integral_density_error = 0;

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
h_nT_ref = plot(nan, nan, 'c--'); % r * n_ref (as in sim_fuelratio.slx)
ylabel('$n_T$', 'Interpreter','latex');
xlim([0 tend]);
legend("$n_T$", "$n_T$ reference", 'Interpreter','latex', 'Location','southeast');

% n_D
nexttile(7); hold on; box on;
h_nD = plot(nan, nan, 'b-');
h_nD_ref = plot(nan, nan, 'c--'); % (1 - r) * n_ref (as in sim_fuelratio.slx)
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
plot(t_vec, r_ideal_vec, 'c--');
ylabel('$r$', 'Interpreter','latex');
xlim([0 tend]);
legend("current ratio", "ideal ratio", 'Interpreter','latex', 'Location','southeast');

% r_hat
nexttile(8); hold on; box on;
h_rhat = plot(nan, nan, 'b-');
plot(t_vec, r_ideal_vec, 'c--');
ylabel('$\hat{r}$', 'Interpreter','latex');
xlabel('$t$ [s]', 'Interpreter','latex');
xlim([0 tend]);
legend("nominal ratio", "ideal ratio", 'Interpreter','latex', 'Location','southeast');

% n_D * n_T vs r_hat
nexttile(3, [2 1]); hold on; box on;
h_P_rhat = plot(nan, nan, 'b-');
h_opt = plot(nan, nan, 'cx', 'MarkerSize', 10, 'LineWidth', 1.5); % moves with r_ideal(t)
yline(0.25 * total_density_reference^2, 'c:');
xlabel('$\hat{r}$', 'Interpreter','latex');
ylabel('$n_D \times n_T$', 'Interpreter','latex');
legend("$n_D \times n_T$", "current optimum", "ideal $n_D \times n_T$", 'Interpreter','latex', 'Location','southeast');

% Total energy
nexttile(9); hold on; box on;
h_E = plot(nan, nan, 'b-');
plot(t_vec, energy_max_vec, 'c--');
ylabel('$\int_0^t n_D n_T \, d\tau$', 'Interpreter','latex');
xlabel('$t$ [s]', 'Interpreter','latex');
xlim([0 tend]);
legend("ESC", "ideal", 'Interpreter','latex', 'Location','southeast');

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
    nD = Ad_D_vec(k) * nD + Bd_D_vec(k) * u_D;
    nT = Ad_T_vec(k) * nT + Bd_T_vec(k) * u_T;

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
        set(h_opt,    'XData', r_ideal_vec(k), 'YData', 0.25 * total_density_reference^2);
        set(h_E,      'XData', tk, 'YData', cumtrapz(tk, P_vec(1:k)));
        drawnow;
    end
end

%% Results
energy_ESC = trapz(t_vec, P_vec);
energy_max = energy_max_vec(end);
fprintf('r_ideal_0 = %.4f, lambda_r_ideal = %.5f 1/s\n', r_ideal_0, lambda_r_ideal);
fprintf('Final r_hat = %.4f, final ideal ratio = %.4f\n', r_hat, r_ideal_vec(end));
fprintf('Total energy: ESC = %.1f, ideal = %.1f (ESC reaches %.2f%%)\n', energy_ESC, energy_max, energy_ESC / energy_max * 100);
