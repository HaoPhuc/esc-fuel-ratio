%% Chosen ESC sets on random plants (follow-up of the fixed-plant analysis)
% MATLAB version of OTO_ESC_chosen_Plant_rand.py. Same settings, same random numbers, same columns;
% the results agree with the Python files to rounding (check: Tools/validate_matlab_ports.m).
%
% Every ESC set below is run on the SAME 100,000 random plants, r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t),
% with r_ideal_0 in [0.45, 0.55] and lambda_r_ideal in [-0.002, 0.002] 1/s. The plants are the ones of the
% MATLAB data set OTO-ESC_fix-1_0.2_6-100kshots.csv (same random numbers, skip = 1812645), so row i is
% the same plant there.
%
% Settings as in OTO_ESC_paired_Plant_fix (not as in OTO_ESC_fix_Plant_rand.m):
%   * every run starts from a plasma that is already running (full density, steady state at r = 0.5);
%   * extra columns tracking_error, tracking_error_late, settling_time_0.01, settling_time_0.02
%     (from the ratio the plasma receives, see Tools/esc_sim.m).
%
% Output (the "-matlab" ending keeps the stored Python files from being replaced)
%   OTO-ESC_chosen-references-100k-matlab.csv     per plant: energy with the ratio fixed at 0.5
%                                                 (energy_const) and with the ratio following
%                                                 r_ideal(t) exactly (energy_ideal)
%   OTO-ESC_chosen-<k>_<a>_<f>-100k-matlab.csv    one file per ESC set
% Rows are in the same order in every file. To use more cores, start several MATLAB sessions with
% different sets_to_run (and run_references = true in only one of them).

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'Tools'));

%% What to run
run_references = true;      % the two reference cases
sets_to_run = 1:5;          % indices in the list of ESC sets below
rows = [];                  % [] = all plants; e.g. 1:25000 for only some of them
output_folder = esc_paths('OTO-ESC_fix');   % data/OTO-ESC_fix/
overwrite = false;          % true: replace existing output files

%% ESC sets: {name, optimizer gain k, dither amplitude a, dither frequency f [Hz]}
% Picked in OTO-Plant_fix-paired.ipynb among the sets with eta >= 0.9 on all eight plants that settle
% within 0.01 on every plant with a late tracking error below 0.005 (values rounded to 3 significant digits).
esc_sets = {
    'reference',               1,      0.2,    6       % chosen from the 3-D plots in OTO-Plant_fix.ipynb
    'fastest',                 0.255,  0.0517, 8.41    % shortest worst settling time
    'fastest, a >= 0.15',      0.265,  0.192,  9.09    % the same with a dither large enough to see in a noisy signal
    'fastest, f <= 3 Hz',      0.0982, 0.0556, 2.97    % the same with a slow dither
    'best energy, a >= 0.1',   1.6,    0.11,   9.91    % highest worst-plant energy score with a >= 0.1
    };

%% Plants (as in OTO_ESC_fix_Plant_rand.m)
combinations = 100000;
seed = 0;
skip = 1812645;             % where the MATLAB session was when it made OTO-ESC_fix-1_0.2_6-100kshots.csv
r_ideal_0_range = [0.45, 0.55];
lambda_r_ideal_range = [-0.002, 0.002];   % [1/s]

%% Simulation settings
tend = 100;                 % [s]
dt = 0.01;                  % [s]
r_hat_0 = 0.5;              % ESC starting fuel ratio
const_ratio = 0.5;          % fixed fuel ratio without ESC
start_ratio = 0.5;          % the plasma has been running at this ratio before t = 0
settle_tolerances = [0.01, 0.02];
N_REF = 11.5;               % total density reference (for energy_max)

%% Plants (randomized); one MATLAB trial calls rand() in this order: r_ideal_0, lambda_r_ideal
esc_rng(seed, skip);
u = esc_draw(combinations, 2);
r_ideal_0 = r_ideal_0_range(1) + diff(r_ideal_0_range) * u(:, 1);
lambda_r_ideal = lambda_r_ideal_range(1) + diff(lambda_r_ideal_range) * u(:, 2);
label = count_label(combinations);
if ~isempty(rows)
    r_ideal_0 = r_ideal_0(rows);
    lambda_r_ideal = lambda_r_ideal(rows);
    label = sprintf('%s-rows%d-%d', label, rows(1), rows(end));
end
plant = {'RIdeal0', r_ideal_0, 'LambdaRIdeal', lambda_r_ideal, 'SteadyStart', start_ratio, 'Dt', dt, 'Tend', tend};

%% References
if run_references
    output = fullfile(output_folder, sprintf('OTO-ESC_chosen-references-%s-matlab.csv', label));
    check_output(output, overwrite);
    fixed = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', const_ratio, 'Progress', 'ratio 0.5', plant{:});
    ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', 'Progress', 'ideal ratio', plant{:});
    esc_write_csv(output, {'r_ideal_0', 'lambda_r_ideal', 'energy_const', 'energy_ideal', 'energy_max'}, ...
                  {r_ideal_0, lambda_r_ideal, fixed.energy, ideal.energy, 0.25 * N_REF^2 * tend});
end

%% ESC sets
for index = sets_to_run
    [set_name, k, a, f] = esc_sets{index, :};
    output = fullfile(output_folder, sprintf('OTO-ESC_chosen-%g_%g_%g-%s-matlab.csv', k, a, f, label));
    check_output(output, overwrite);
    esc = esc_sim(k, a, f, 'RHat0', r_hat_0, 'Track', true, 'SettleTolerances', settle_tolerances, ...
                  'Progress', set_name, plant{:});
    names = {'optimizer_gain', 'dither_amplitude', 'dither_frequency', 'r_ideal_0', 'lambda_r_ideal', ...
             'energy_ESC', 'tracking_error', 'tracking_error_late'};
    columns = {k, a, f, r_ideal_0, lambda_r_ideal, esc.energy, esc.tracking_error, esc.tracking_error_late};
    for j = 1:numel(settle_tolerances)
        names{end + 1} = sprintf('settling_time_%g', settle_tolerances(j)); %#ok<SAGROW>
        columns{end + 1} = esc.settling_time(:, j); %#ok<SAGROW>
    end
    names = [names, {'converged', 'convergence_time'}];
    columns = [columns, {esc.converged, esc.convergence_time}];
    esc_write_csv(output, names, columns);
end


%% Local functions
function check_output(output, overwrite)
if isfile(output) && ~overwrite
    error('%s exists already. Set overwrite = true to replace it.', output);
end
end

function label = count_label(n)
% 100000 -> '100k', 500 -> '500'
if mod(n, 1000) == 0
    label = sprintf('%dk', n / 1000);
else
    label = sprintf('%d', n);
end
end
