%% Paired fixed-plant sweep: the SAME random ESC parameter sets on every fixed plant
% MATLAB version of OTO_ESC_paired_Plant_fix.py. Same settings, same random numbers (MATLAB's default
% stream), same columns; the results agree with the Python files to rounding
% (check: Tools/validate_matlab_ports.m).
%
% Differences from OTO_ESC_rand_Plant_fix.m:
%   * every plant gets the same ESC parameter sets, so one set can be followed across plants;
%   * the sets are drawn only where ESC is useful: k 0.02-5 (log-uniform), a 0-0.6, f 1.5-10 Hz;
%   * every run starts from a plasma that is already running (full density, steady state with the
%     fuel ratio at 0.5) instead of the 25 % deuterium-rich start;
%   * extra columns:
%       energy_ideal         energy when the ratio follows r_ideal(t) exactly (best possible)
%       tracking_error       mean distance between the ratio the plasma receives (averaged over a
%                            whole number of dither periods) and r_ideal, over the run
%       tracking_error_late  the same over the second half of the run
%       settling_time_0.01   time after which that distance stays below 0.01 (NaN: never)
%       settling_time_0.02   the same for 0.02
%   converged and convergence_time (5 % band on r_hat) are kept for comparison.
%
% Output: one file per plant, OTO-paired-<r_ideal_0>_<lambda>-40k-matlab.csv, rows in the same order
% in every file (row i is the same ESC set everywhere). The "-matlab" ending keeps the stored
% Python files from being replaced.
%
% The simulation is in Tools/esc_sim.m (vectorised: many runs at once). To use more cores, start
% several MATLAB sessions with different values of plants_to_run.

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'Tools'));

%% Batch sweep settings
combinations = 40000;       % ESC parameter sets (each is run on every plant)
seed = 0;                   % 0 = the random numbers of a freshly started MATLAB (rng('default'))
plants_to_run = 1:8;        % indices in the plant list below
output_folder = here;
overwrite = false;          % true: replace existing output files

%% Plants: [r_ideal_0, lambda_r_ideal [1/s]];  r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t)
plants = [0.5,    0.001;
          0.5,   -0.001;
          0.55,   0.002;
          0.45,  -0.002;
          0.525,  0.0;
          0.475,  0.0;
          0.5375, -0.0015;
          0.4625, 0.0015];

%% Simulation settings
tend = 100;                 % [s]
dt = 0.01;                  % [s]
r_hat_0 = 0.5;              % ESC starting fuel ratio
const_ratio = 0.5;          % fixed fuel ratio without ESC
start_ratio = 0.5;          % the plasma has been running at this ratio before t = 0
settle_tolerances = [0.01, 0.02];
N_REF = 11.5;               % total density reference (for energy_max)

%% ESC parameter ranges (the region where ESC is useful)
optimizer_gain_range = [0.02, 5];
dither_amplitude_range = [0, 0.6];
dither_frequency_range = [1.5, 10];

%% ESC parameters (randomized); the same numbers for every plant
% one trial draws amplitude, frequency and gain, in this order
esc_rng(seed, 0);
u = esc_draw(combinations, 3);
dither_amplitude = dither_amplitude_range(1) + diff(dither_amplitude_range) * u(:, 1);
dither_frequency = dither_frequency_range(1) + diff(dither_frequency_range) * u(:, 2);
log_range = log10(optimizer_gain_range);
optimizer_gain = 10 .^ (log_range(1) + diff(log_range) * u(:, 3));

%% Run the plants
for index = plants_to_run
    r_ideal_0 = plants(index, 1);
    lambda_r_ideal = plants(index, 2);
    tag = plant_tag(r_ideal_0, lambda_r_ideal);
    output = fullfile(output_folder, sprintf('OTO-paired-%s-%s-matlab.csv', tag, count_label(combinations)));
    if isfile(output) && ~overwrite
        error('%s exists already. Set overwrite = true to replace it.', output);
    end
    plant = {'RIdeal0', r_ideal_0, 'LambdaRIdeal', lambda_r_ideal, 'SteadyStart', start_ratio, 'Dt', dt, 'Tend', tend};

    % references on this plant: ratio fixed at 0.5, and ratio following r_ideal(t) exactly
    fixed = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', const_ratio, plant{:});
    ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', plant{:});

    esc = esc_sim(optimizer_gain, dither_amplitude, dither_frequency, 'RHat0', r_hat_0, 'Track', true, ...
                  'SettleTolerances', settle_tolerances, 'Progress', sprintf('plant %s', tag), plant{:});

    names = {'optimizer_gain', 'dither_amplitude', 'dither_frequency', 'r_ideal_0', 'lambda_r_ideal', ...
             'energy_ESC', 'energy_const', 'energy_ideal', 'energy_max', 'choose_ESC', ...
             'tracking_error', 'tracking_error_late'};
    columns = {optimizer_gain, dither_amplitude, dither_frequency, r_ideal_0, lambda_r_ideal, ...
               esc.energy, fixed.energy, ideal.energy, 0.25 * N_REF^2 * tend, esc.energy > fixed.energy, ...
               esc.tracking_error, esc.tracking_error_late};
    for j = 1:numel(settle_tolerances)
        names{end + 1} = sprintf('settling_time_%g', settle_tolerances(j)); %#ok<SAGROW>
        columns{end + 1} = esc.settling_time(:, j); %#ok<SAGROW>
    end
    names = [names, {'converged', 'convergence_time'}];
    columns = [columns, {esc.converged, esc.convergence_time}];
    esc_write_csv(output, names, columns);
end


%% Local functions
function tag = plant_tag(r_ideal_0, lambda_r_ideal)
% '0.5_0.001', '0.525' (no drift: no lambda in the name), as in the Python script
tag = sprintf('%g', r_ideal_0);
if lambda_r_ideal ~= 0
    tag = sprintf('%s_%g', tag, lambda_r_ideal);
end
end

function label = count_label(n)
% 40000 -> '40k', 500 -> '500'
if mod(n, 1000) == 0
    label = sprintf('%dk', n / 1000);
else
    label = sprintf('%d', n);
end
end
