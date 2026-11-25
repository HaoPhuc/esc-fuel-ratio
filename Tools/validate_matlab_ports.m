%% Check the MATLAB simulator and the MATLAB versions of the Python sweep scripts
% Re-simulates the first rows of stored data sets with Tools/esc_sim.m and compares:
%   A. OTO-ESC_fix-1_0.2_6-100kshots.csv   made by the original MATLAB script OTO_ESC_fix_Plant_rand.m
%   B. OTO-paired-*-40k.csv                 made by OTO_ESC_paired_Plant_fix.py
%   C. OTO-ESC_chosen-*-100k.csv            made by OTO_ESC_chosen_Plant_rand.py
%   D. OTO-losing_region-*.csv              made by OTO_ESC_losing_region.py
%   E. OTO-mirror_symmetry_test.csv         made by mirror_symmetry_test.py
%   F. OTO-crossed-*.csv                    made by OTO_ESC_crossed.py (also checks the drift shapes and
%                                           time scales of esc_sim.m)
% For every quantity it prints the largest difference and the share of rows that agree. The random
% parameters (A to C) must agree exactly (to the rounding of the CSV files); the results should agree
% for at least 99 % of the rows: a few runs per thousand are sensitive to rounding errors (large gain,
% small dither amplitude) and can end up a little differently in any two programs.
% Run time: about two minutes.

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(here);
n_rows = 200;
read = @(name) readtable(esc_paths('file', name), 'VariableNamingRule', 'preserve');   % found under data/
report = {};

%% A. original MATLAB data set (plants and ESC energies)
ref = read('OTO-ESC_fix-1_0.2_6-100kshots.csv'); ref = ref(1:n_rows, :);
esc_rng(0, 1812645);
u = esc_draw(n_rows, 2);
r0 = 0.45 + diff([0.45, 0.55]) * u(:, 1);            % as in the sweep scripts
lam = -0.002 + diff([-0.002, 0.002]) * u(:, 2);
report = check(report, 'A: MATLAB data', 'r_ideal_0 (random stream)', r0, ref.r_ideal_0, 'rel', 1e-12);
report = check(report, 'A: MATLAB data', 'lambda_r_ideal', lam, ref.lambda_r_ideal, 'rel', 1e-12);
out = esc_sim(1, 0.2, 6, 'RIdeal0', r0, 'LambdaRIdeal', lam, 'RHat0', 0.5);
fixed = esc_sim(1, 0.1, 1, 'RIdeal0', r0, 'LambdaRIdeal', lam, 'UseESC', false);
report = check(report, 'A: MATLAB data', 'energy_ESC', out.energy, ref.energy_ESC, 'rel', 1e-9);
report = check(report, 'A: MATLAB data', 'energy_const', fixed.energy, ref.energy_const, 'rel', 1e-9);
report = check(report, 'A: MATLAB data', 'converged', double(out.converged), ref.converged, 'abs', 0);
report = check(report, 'A: MATLAB data', 'convergence_time', out.convergence_time, ref.convergence_time, 'abs', 0.011);

%% B. paired fixed-plant sweep (Python)
esc_rng(0, 0);
u = esc_draw(n_rows, 3);
a = 0 + diff([0, 0.6]) * u(:, 1);
f = 1.5 + diff([1.5, 10]) * u(:, 2);
k = 10 .^ (log10(0.02) + diff(log10([0.02, 5])) * u(:, 3));
for plant = {'0.5375_-0.0015', 0.5375, -0.0015; '0.4625_0.0015', 0.4625, 0.0015; '0.55_0.002', 0.55, 0.002}'
    [tag, r0, lam] = plant{:};
    ref = read(sprintf('OTO-paired-%s-40k.csv', tag)); ref = ref(1:n_rows, :);
    label = ['B: paired ' tag];
    report = check(report, label, 'ESC parameters (random stream)', [k; a; f], ...
                   [ref.optimizer_gain; ref.dither_amplitude; ref.dither_frequency], 'rel', 1e-12);
    opts = {'RIdeal0', r0, 'LambdaRIdeal', lam, 'SteadyStart', 0.5};
    out = esc_sim(k, a, f, 'RHat0', 0.5, 'Track', true, opts{:});
    fixed = esc_sim(1, 0.1, 1, 'UseESC', false, opts{:});
    ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', opts{:});
    report = check(report, label, 'energy_ESC', out.energy, ref.energy_ESC, 'rel', 1e-9);
    report = check(report, label, 'energy_const, energy_ideal', [fixed.energy; ideal.energy], ...
                   [ref.energy_const(1); ref.energy_ideal(1)], 'rel', 1e-9);
    report = check(report, label, 'tracking_error, _late', [out.tracking_error; out.tracking_error_late], ...
                   [ref.tracking_error; ref.tracking_error_late], 'abs', 1e-9);
    report = check(report, label, 'settling_time_0.01, _0.02', out.settling_time(:), ...
                   [ref.('settling_time_0.01'); ref.('settling_time_0.02')], 'abs', 0.011);
    report = check(report, label, 'convergence_time', out.convergence_time, ref.convergence_time, 'abs', 0.011);
end

%% C. chosen ESC sets on random plants (Python)
ref = read('OTO-ESC_chosen-references-100k.csv'); ref = ref(1:n_rows, :);
esc_rng(0, 1812645);
u = esc_draw(n_rows, 2);
r0 = 0.45 + diff([0.45, 0.55]) * u(:, 1);            % as in the sweep scripts
lam = -0.002 + diff([-0.002, 0.002]) * u(:, 2);
report = check(report, 'C: chosen references', 'plants (random stream)', [r0; lam], ...
               [ref.r_ideal_0; ref.lambda_r_ideal], 'rel', 1e-12);
opts = {'RIdeal0', r0, 'LambdaRIdeal', lam, 'SteadyStart', 0.5};
fixed = esc_sim(1, 0.1, 1, 'UseESC', false, opts{:});
ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', opts{:});
report = check(report, 'C: chosen references', 'energy_const', fixed.energy, ref.energy_const, 'rel', 1e-9);
report = check(report, 'C: chosen references', 'energy_ideal', ideal.energy, ref.energy_ideal, 'rel', 1e-9);
for chosen_set = {'1_0.2_6', 1, 0.2, 6; '0.255_0.0517_8.41', 0.255, 0.0517, 8.41; '0.0982_0.0556_2.97', 0.0982, 0.0556, 2.97}'
    [tag, k, a, f] = chosen_set{:};
    ref = read(sprintf('OTO-ESC_chosen-%s-100k.csv', tag)); ref = ref(1:n_rows, :);
    label = ['C: chosen ' tag];
    out = esc_sim(k, a, f, 'RHat0', 0.5, 'Track', true, opts{:});
    report = check(report, label, 'energy_ESC', out.energy, ref.energy_ESC, 'rel', 1e-9);
    report = check(report, label, 'tracking_error, _late', [out.tracking_error; out.tracking_error_late], ...
                   [ref.tracking_error; ref.tracking_error_late], 'abs', 1e-9);
    report = check(report, label, 'settling_time_0.01, _0.02', out.settling_time(:), ...
                   [ref.('settling_time_0.01'); ref.('settling_time_0.02')], 'abs', 0.011);
end

%% D. losing-region grid (Python)
for case_ = {'steady-T200', 'matlab-T100'}
    ref = read(sprintf('OTO-losing_region-%s.csv', case_{1}));
    ref = ref(1:41:end, :);          % every 41st plant of the grid
    tend = ref.tend(1);
    opts = {'RIdeal0', ref.r_ideal_0, 'LambdaRIdeal', ref.lambda_r_ideal, 'Tend', tend};
    if startsWith(case_{1}, 'steady')
        opts = [opts, {'SteadyStart', 0.5}]; %#ok<AGROW>
    end
    out = esc_sim(1, 0.2, 6, 'RHat0', 0.5, opts{:});
    fixed = esc_sim(1, 0.1, 1, 'UseESC', false, opts{:});
    ideal = esc_sim(1, 0.1, 1, 'UseESC', false, 'FixedRatio', 'ideal', opts{:});
    label = ['D: losing region ' case_{1}];
    report = check(report, label, 'energy_ESC', out.energy, ref.energy_ESC, 'rel', 1e-9);
    report = check(report, label, 'energy_const, energy_ideal', [fixed.energy; ideal.energy], ...
                   [ref.energy_const; ref.energy_ideal], 'rel', 1e-9);
end

%% E. mirror symmetry test (Python)
ref_all = read('OTO-mirror_symmetry_test.csv');
pairs = {'0.5 up 0.001', 0.5, 0.001, 0.5, -0.001; '0.525', 0.525, 0, 0.475, 0};
variants = {'energy_A', 'A', {}; 'energy_B_flip', 'B', {'DitherPhase', pi}; 'energy_B_init', 'B', {'InitialRatio', 0.9};
            'energy_A_mirror', 'A', {'MirrorPlant', true, 'DitherPhase', pi, 'InitialRatio', 0.9}; 'energy_B_sym', 'B', {'InitialRatio', 0.5}};
for p = 1:size(pairs, 1)
    [name_A, r0_A, lam_A, r0_B, lam_B] = pairs{p, :};
    ref = ref_all(strcmp(string(ref_all.plant_A), name_A), :); ref = ref(1:50, :);
    for v = 1:size(variants, 1)
        [column, which, options] = variants{v, :};
        if which == 'A', plant = {'RIdeal0', r0_A, 'LambdaRIdeal', lam_A}; else, plant = {'RIdeal0', r0_B, 'LambdaRIdeal', lam_B}; end
        out = esc_sim(ref.optimizer_gain, ref.dither_amplitude, ref.dither_frequency, 'RHat0', 0.5, plant{:}, options{:});
        report = check(report, ['E: mirror test ' name_A], column, out.energy, ref.(column), 'rel', 1e-9);
    end
end

%% F. crossed sweep (Python): quasi-random ESC sets, random plants, and some rows of seven blocks
sets = read('OTO-crossed-sets.csv'); plants = read('OTO-crossed-plants.csv'); refs = read('OTO-crossed-references.csv');
n_q = height(sets) - 5;                                % the first five sets are the chosen ones
kaf = [10 .^ (log10(1e-3) + diff(log10([1e-3, 5])) * halton(n_q, 2)); 0.005 + diff([0.005, 0.6]) * halton(n_q, 3); ...
       0.5 + diff([0.5, 10]) * halton(n_q, 5)];
report = check(report, 'F: crossed tables', 'ESC sets (quasi-random stream)', kaf, ...
               [sets.optimizer_gain(6:end); sets.dither_amplitude(6:end); sets.dither_frequency(6:end)], 'rel', 1e-12);
is_random = strcmp(plants.family, 'random');
esc_rng(0, 0);
u = esc_draw(sum(is_random), 2);
report = check(report, 'F: crossed tables', 'random plants (random stream)', ...
               [0.45 + diff([0.45, 0.55]) * u(:, 1); -0.002 + diff([-0.002, 0.002]) * u(:, 2)], ...
               [plants.r_ideal_0(is_random); plants.lambda_r_ideal(is_random)], 'rel', 1e-12);
for block = {'linear', 'step', 'sine', 'timescale', 'random1', 'from0.7', 'dt0.002'}
    name = block{1};
    ref = read(sprintf('OTO-crossed-%s.csv', name));
    ref = ref(unique([(1:60)'; find(ref.set == ref.set(1))]), :);   % 60 sets on the first plant, one set on every plant
    pl = plants(ref.plant + 1, :); st = sets(ref.set + 1, :);
    rf = refs(strcmp(refs.block, name), :);
    [~, where] = ismember(ref.plant, rf.plant);
    start = 0.5; step = 0.01;
    if startsWith(name, 'from'), start = str2double(name(5:end)); end
    if strcmp(name, 'dt0.002'), step = 0.002; end
    opts = {'RIdeal0', pl.r_ideal_0, 'LambdaRIdeal', pl.lambda_r_ideal, 'DriftShape', pl.drift_shape, ...
            'DriftSize', pl.drift_size, 'DriftTime', pl.drift_time, 'TauScale', pl.tau_scale, 'SteadyStart', start, 'Dt', step};
    out = esc_sim(st.optimizer_gain, st.dither_amplitude, st.dither_frequency, 'RHat0', start, 'Track', true, opts{:});
    fixed = esc_sim(0, 0, 1, 'UseESC', false, opts{:});
    ideal = esc_sim(0, 0, 1, 'UseESC', false, 'FixedRatio', 'ideal', opts{:});
    label = ['F: crossed ' name];
    report = check(report, label, 'energy_const, energy_ideal', [fixed.energy; ideal.energy], ...
                   [rf.energy_const(where); rf.energy_ideal(where)], 'rel', 1e-9);
    report = check(report, label, 'energy_ESC', out.energy, rf.energy_const(where) + ref.energy_gain, 'rel', 1e-9);
    report = check(report, label, 'converged', double(out.converged), ref.converged, 'abs', 0);
    report = check(report, label, 'tracking_error, _late', [out.tracking_error; out.tracking_error_late], ...
                   [ref.tracking_error; ref.tracking_error_late], 'rel', 1e-5);   % stored with 6 digits
    report = check(report, label, 'settling_time_0.01, _0.02', out.settling_time(:), ...
                   [ref.('settling_time_0.01'); ref.('settling_time_0.02')], 'abs', step + 0.001);
    report = check(report, label, 'convergence_time', out.convergence_time, ref.convergence_time, 'abs', step + 0.001);
end

%% Summary
fprintf('\n%-32s %-34s %6s %14s %10s  %s\n', 'check', 'quantity', 'values', 'largest diff', 'agree', 'result');
n_fail = 0;
for j = 1:size(report, 1)
    [label, quantity, n, largest, share, exact] = report{j, :};
    if exact
        ok = share == 1;
    else
        ok = share >= 0.99;
    end
    n_fail = n_fail + ~ok;
    verdict = 'ok';
    if ~ok, verdict = 'CHECK'; end
    fprintf('%-32s %-34s %6d %14.3g %9.1f%%  %s\n', label, quantity, n, largest, 100 * share, verdict);
end
if n_fail == 0
    fprintf('\nAll checks passed: the MATLAB code reproduces the stored data sets.\n');
else
    fprintf('\n%d check(s) below the limit; see the rows marked CHECK.\n', n_fail);
end


%% Local functions
function v = halton(n, base)
% points 1..n of the van der Corput sequence in `base` (as in OTO_ESC_crossed.m)
i = (1:n)'; scale = ones(n, 1); v = zeros(n, 1);
while any(i > 0)
    scale = scale / base; v = v + scale .* mod(i, base); i = floor(i / base);
end
end

function report = check(report, label, quantity, value, reference, kind, tolerance)
% Compare two vectors. 'rel': relative difference, 'abs': absolute difference. NaN equals NaN.
value = double(value(:)); reference = double(reference(:));
both_nan = isnan(value) & isnan(reference);
if strcmp(kind, 'rel')
    diff_ = abs(value - reference) ./ max(abs(reference), realmin);
else
    diff_ = abs(value - reference);
end
diff_(both_nan) = 0;
diff_(isnan(diff_)) = inf;           % NaN on one side only
share = mean(diff_ <= tolerance);
exact = contains(quantity, 'random stream');   % the parameters must agree in every row
report(end + 1, :) = {label, quantity, numel(value), max(diff_), share, exact};
end
