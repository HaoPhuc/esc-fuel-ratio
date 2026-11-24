%% Where does ESC lose against r = 0.5? One ESC set on a regular grid of plants near r_ideal = 0.5
% MATLAB version of OTO_ESC_losing_region.py. Same settings, same grid, same columns; the results agree
% with the Python files to rounding (check: Tools/validate_matlab_ports.m).
%
% The plants are r_ideal(t) = r_ideal_0 * exp(lambda_r_ideal * t) on a grid of r_ideal_0 and lambda_r_ideal
% around (0.5, 0), where the region in which ESC loses lies (see OTO-ESC_fix.ipynb, Section 8). Four cases:
%
%     steady-T50, steady-T100, steady-T200   runs of 50, 100 and 200 s that start from a plasma already
%                                            running at r = 0.5 (as in OTO_ESC_chosen_Plant_rand)
%     matlab-T100                            runs of 100 s with the start of the original MATLAB scripts
%                                            (25 % density, deuterium-rich)
%
% For every plant: energy with ESC, with the ratio fixed at 0.5 (energy_const) and with the ratio
% following r_ideal(t) exactly (energy_ideal).
%
% Output: OTO-losing_region-<case>-matlab.csv, one row per plant, in the same order as the Python files
% (r_ideal_0 varies slowest). The "-matlab" ending keeps the stored Python files from being replaced.

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'Tools'));

%% What to run
cases_to_run = 1:4;         % indices in the list of cases below
output_folder = here;
overwrite = false;          % true: replace existing output files

%% ESC set (the reference set of OTO-ESC_fix.ipynb)
optimizer_gain = 1;
dither_amplitude = 0.2;
dither_frequency = 6;       % [Hz]

%% Plant grid
r_ideal_0_grid = linspace(0.48, 0.52, 81);          % step 0.0005
lambda_r_ideal_grid = linspace(-1e-3, 1e-3, 101);   % step 2e-5 [1/s]

%% Cases: {name, run length [s], start}
cases = {
    'steady-T50',   50,  'steady'
    'steady-T100',  100, 'steady'
    'steady-T200',  200, 'steady'
    'matlab-T100',  100, 'matlab'
    };

dt = 0.01;                  % [s]
r_hat_0 = 0.5;              % ESC starting fuel ratio
const_ratio = 0.5;          % fixed fuel ratio without ESC
start_ratio = 0.5;          % steady start: the plasma has been running at this ratio before t = 0

%% Grid as a list of plants: lambda varies fastest, as in the Python file
[lambda_all, r0_all] = ndgrid(lambda_r_ideal_grid, r_ideal_0_grid);
r_ideal_0 = r0_all(:);
lambda_r_ideal = lambda_all(:);

for index = cases_to_run
    [name, tend, start] = cases{index, :};
    output = fullfile(output_folder, sprintf('OTO-losing_region-%s-matlab.csv', name));
    if isfile(output) && ~overwrite
        error('%s exists already. Set overwrite = true to replace it.', output);
    end
    plant = {'RIdeal0', r_ideal_0, 'LambdaRIdeal', lambda_r_ideal, 'Dt', dt, 'Tend', tend};
    if strcmp(start, 'steady')
        plant = [plant, {'SteadyStart', start_ratio}]; %#ok<AGROW>
    end
    fixed = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', const_ratio, 'Progress', [name ': ratio 0.5'], plant{:});
    ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', 'Progress', [name ': ideal ratio'], plant{:});
    esc = esc_sim(optimizer_gain, dither_amplitude, dither_frequency, 'RHat0', r_hat_0, ...
                  'Progress', [name ': ESC'], plant{:});
    esc_write_csv(output, ...
        {'case', 'tend', 'start', 'optimizer_gain', 'dither_amplitude', 'dither_frequency', ...
         'r_ideal_0', 'lambda_r_ideal', 'energy_ESC', 'energy_const', 'energy_ideal'}, ...
        {name, tend, start, optimizer_gain, dither_amplitude, dither_frequency, ...
         r_ideal_0, lambda_r_ideal, esc.energy, fixed.energy, ideal.energy});
end
