%% Prerequisies
clc; clear all; close all;

%% ESC parameters
% Most important parameters
dither_amplitude = 0.1;
dither_freqeuncy = 0.1;
optimizer_gain = 3e-4;

% Remaining parameters
dither_omega = dither_freqeuncy * 2 * pi;
highpass_cutoff_omega = dither_omega / pi;
lowpass_cutoff_omega = dither_omega / pi;
initial_ratio = 0.1;

%% Settings and background-calculations
% Time
tend = 100;
dt = 0.01;

% Dynamics
n_D_decay_rate = 1/1.71;
n_T_decay_rate = 1/1.66;

% Density controller
proportional_gain = 3.129;
integral_gain = 2.482;
total_density_reference = 11.5; % e19 removed for numerical stability
greenwald_density_limit = 11.9; % e19 removed for numerical stability

% Calculate transfer function of dynamics and discretize
n_D_dynamics = ss(-n_D_decay_rate, 1, 1, 0); % dx/dt = A*x + B*u   ;   y = C*x + D*u
n_T_dynamics = ss(-n_T_decay_rate, 1, 1, 0);
n_D_dynamics_discretized = c2d(n_D_dynamics, dt);
n_T_dynamics_discretized = c2d(n_T_dynamics, dt);

% Calculate transfer functions of extremum seeking control and discretize
highpass_filter = tf([1, 0], [1, highpass_cutoff_omega]);
highpass_filter_discretized = c2d(highpass_filter, dt);
lowpass_filter = tf(lowpass_cutoff_omega, [1, lowpass_cutoff_omega]);
lowpass_filter_discretized = c2d(lowpass_filter, dt);

% Calculate initial steady state conditions
initial_nD = 0.25 * (1-initial_ratio) * total_density_reference;
initial_nT = 0.25 * initial_ratio * total_density_reference;

% Ideal fuel ration
ideal_ratio = n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate);

%% Run simulation
out = sim('sim_fuelratio.slx', tend);

%% Plotting
close all;
figure("Position",[200 200 1200 400])
tile = tiledlayout(3, 3);
t = 0:dt:tend;
t_zoom = [0, tend];
ESC_list = ["ss"];
color_list = ["blue", "red", "cyan", "yellow", "maroon", "green"];

for i = 1:length(ESC_list)
    nexttile(1)
    plot(t, out.(ESC_list(i) + "_nD_plus_nT"), color_list(i))
    hold on

    nexttile(4)
    plot(t, out.(ESC_list(i) + "_nT"), color_list(i))
    hold on
    plot(t, out.(ESC_list(i) + "_nT_ref"), "c--")
    
    nexttile(7)
    plot(t, out.(ESC_list(i) + "_nD"), color_list(i))
    hold on
    plot(t, out.(ESC_list(i) + "_nD_ref"),"c--")

    nexttile(2)
    plot(t, out.(ESC_list(i) + "_nD_times_nT"), color_list(i))
    hold on

    nexttile(5)
    plot(t, out.(ESC_list(i) + "_ratio"), color_list(i))
    hold on

    nexttile(8)
    plot(t, out.(ESC_list(i) + "_ratio_hat"), color_list(i))
    hold on

    nexttile(3, [3 1])
    plot(out.(ESC_list(i) + "_nD"), out.(ESC_list(i) + "_nT"), color_list(i))
    hold on
end

nexttile(1)
yline(total_density_reference, 'c--')
yline(greenwald_density_limit, 'r--')
ylabel('$n_D + n_T$', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("$n_D + n_T$", "$n_D + n_T$ reference", "greenwald density", "interpreter", "latex", "Location", "southeast")

nexttile(4)
ylabel('$n_T$', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("$n_T$", "$n_T$ reference", "interpreter", "latex", "Location", "southeast")

nexttile(7)
ylabel('$n_D$', 'Interpreter','latex')
xlabel('$t$ [s]', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("$n_D$", "$n_D$ reference", "interpreter", "latex", "Location", "southeast")

nexttile(2)
yline(0.25 * total_density_reference^2, 'c--')
ylabel('$n_D \times n_T$', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("$n_D \times n_T$", "ideal $n_D \times n_T$", "interpreter", "latex", "Location", "southeast")

nexttile(5)
yline(ideal_ratio, 'c--')
ylabel('$r$', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("current ratio", "ideal ratio", "interpreter", "latex", "Location", "southeast")

nexttile(8)
yline(ideal_ratio, 'c--')
ylabel('$\hat{r}$', 'Interpreter','latex')
xlabel('$t$ [s]', 'Interpreter','latex')
box on
xlim(t_zoom)
legend("nominal ratio", "ideal ratio", "interpreter", "latex", "Location", "southeast")

nexttile(3, [3, 1])
lim = axis;
plot([min(lim), max(lim)], total_density_reference - [min(lim), max(lim)], "c--")
plot([min(lim), max(lim)], greenwald_density_limit - [min(lim), max(lim)], "r--")
plot(0.5 * total_density_reference, 0.5 * total_density_reference, "gx", 'MarkerSize',10)
axis([min(lim), max(lim), min(lim), max(lim)])
xlabel('$n_D$', 'Interpreter','latex')
ylabel('$n_T$', 'Interpreter','latex')
box on
legend("$n_D$ and $n_T$", "density reference", "greenwald density", "optimum", "interpreter", "latex", "Location","west")
