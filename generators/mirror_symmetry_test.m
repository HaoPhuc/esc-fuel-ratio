%% Why do mirror plants give different results? A symmetry test
% MATLAB version of mirror_symmetry_test.py. Same settings, same columns; the results agree with the
% Python file to rounding (check: Tools/validate_matlab_ports.m).
%
% The model is unchanged when deuterium and tritium are exchanged (r -> 1 - r), provided that
% everything else is exchanged too. In the stored sweeps three things are NOT exchanged between a
% plant and its mirror twin:
%   1. the dither starts upwards in both (r = r_hat + a sin(w t)); the mirror image would start downwards;
%   2. the initial densities are deuterium-rich in both (set with r = 0.1); the mirror image would be
%      tritium-rich (r = 0.9);
%   3. for the drifting plants, r_ideal_0 exp(lambda t) of the twin is not exactly 1 - r_ideal(t) of the plant.
%
% This script simulates plant A of each pair and its twin B with the same ESC parameters (the first
% n_runs rows of plant A's data set), and repeats B with the dither flipped, with the initial densities
% mirrored, and with both. energy_A_mirror is the exact mirror image of A (all three items exchanged);
% it equals energy_A up to rounding. energy_A_sym and energy_B_sym start both plants from equal D and T
% densities (r = 0.5), so that the direction of the dither is the only difference left for the plants
% without drift. The const_* columns are the benchmark (fuel ratio fixed at 0.5) for the same plant and
% initial state.
%
% Output: OTO-mirror_symmetry_test-matlab.csv (one row per pair and ESC parameter set). The "-matlab"
% ending keeps the stored Python file from being replaced.

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'Tools'));

%% Settings
n_runs = 10000;             % ESC parameter sets per pair
pairs_to_run = 1:4;         % indices in the list of pairs below
r_hat_0 = 0.5;              % as in the optimal-to-operate sweeps
output = fullfile(esc_paths('OTO-Plant_fix'), 'OTO-mirror_symmetry_test-matlab.csv');
overwrite = false;          % true: replace an existing output file

%% Mirror pairs: {name A, r_ideal_0 A, lambda A, file tag of A, name B, r_ideal_0 B, lambda B}
pairs = {
    '0.5 up 0.001',       0.5,    0.001,  '0.5_0.001',      '0.5 down 0.001',   0.5,    -0.001
    '0.55 up 0.002',      0.55,   0.002,  '0.55_0.002',     '0.45 down 0.002',  0.45,   -0.002
    '0.525',              0.525,  0.0,    '0.525',          '0.475',            0.475,  0.0
    '0.5375 down 0.0015', 0.5375, -0.0015, '0.5375_-0.0015', '0.4625 up 0.0015', 0.4625, 0.0015
    };

%% Variants: {column, plant, options that differ from the stored sweeps}
variants = {
    'energy_A',        'A', {}
    'energy_B',        'B', {}
    'energy_B_flip',   'B', {'DitherPhase', pi}
    'energy_B_init',   'B', {'InitialRatio', 0.9}
    'energy_B_both',   'B', {'DitherPhase', pi, 'InitialRatio', 0.9}
    'energy_A_mirror', 'A', {'MirrorPlant', true, 'DitherPhase', pi, 'InitialRatio', 0.9}
    'energy_A_sym',    'A', {'InitialRatio', 0.5}
    'energy_B_sym',    'B', {'InitialRatio', 0.5}
    };

if isfile(output) && ~overwrite
    error('%s exists already. Set overwrite = true to replace it.', output);
end

plant_A = {}; plant_B = {};
values = struct('optimizer_gain', [], 'dither_amplitude', [], 'dither_frequency', []);
for v = 1:size(variants, 1)
    values.(variants{v, 1}) = [];
end
const_names = {'const_A', 'const_B', 'const_B_init', 'const_A_sym', 'const_B_sym'};
for c = 1:numel(const_names)
    values.(const_names{c}) = [];
end

for index = pairs_to_run
    [name_A, r0_A, lam_A, tag, name_B, r0_B, lam_B] = pairs{index, :};
    % ESC parameters: the first n_runs rows of plant A's sweep
    sweep = readtable(esc_paths('file', sprintf('OTO-Plant_fix-%s-100kshots.csv', tag)));
    k = sweep.optimizer_gain(1:n_runs);
    a = sweep.dither_amplitude(1:n_runs);
    f = sweep.dither_frequency(1:n_runs);
    plant_A = [plant_A; repmat({name_A}, n_runs, 1)]; %#ok<AGROW>
    plant_B = [plant_B; repmat({name_B}, n_runs, 1)]; %#ok<AGROW>
    values.optimizer_gain = [values.optimizer_gain; k];
    values.dither_amplitude = [values.dither_amplitude; a];
    values.dither_frequency = [values.dither_frequency; f];

    for v = 1:size(variants, 1)
        [column, which, options] = variants{v, :};
        if which == 'A'
            plant = {'RIdeal0', r0_A, 'LambdaRIdeal', lam_A};
        else
            plant = {'RIdeal0', r0_B, 'LambdaRIdeal', lam_B};
        end
        out = esc_sim(k, a, f, 'RHat0', r_hat_0, plant{:}, options{:});
        values.(column) = [values.(column); out.energy];
        fprintf('%s: %s done\n', name_A, column);
    end

    % benchmark (r = 0.5) for every case; the dither does not enter, the initial state does
    const = [fixed_ratio_energy(r0_A, lam_A, 0.1), fixed_ratio_energy(r0_B, lam_B, 0.1), ...
             fixed_ratio_energy(r0_B, lam_B, 0.9), fixed_ratio_energy(r0_A, lam_A, 0.5), ...
             fixed_ratio_energy(r0_B, lam_B, 0.5)];
    for c = 1:numel(const_names)
        values.(const_names{c}) = [values.(const_names{c}); repmat(const(c), n_runs, 1)];
    end
end

names = [{'plant_A', 'plant_B', 'optimizer_gain', 'dither_amplitude', 'dither_frequency'}, ...
         variants(:, 1)', const_names];
columns = cell(1, numel(names));
columns{1} = plant_A; columns{2} = plant_B;
for j = 3:numel(names)
    columns{j} = values.(names{j});
end
esc_write_csv(output, names, columns);


%% Local functions
function energy = fixed_ratio_energy(r0, lam, initial_ratio)
% Energy of the same plant with the fuel ratio fixed at 0.5 (the benchmark).
out = esc_sim(1, 0.1, 1, 'RIdeal0', r0, 'LambdaRIdeal', lam, 'UseESC', false, 'InitialRatio', initial_ratio);
energy = out.energy(1);
end
