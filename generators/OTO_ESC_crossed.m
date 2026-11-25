%% Crossed sweep: every ESC parameter set on every plant
% MATLAB version of OTO_ESC_crossed.py (see its header for the full description). Same ESC sets, same
% plants, same blocks and columns; the results agree with the Python files to rounding
% (check: Tools/validate_matlab_ports.m).
%
% ESC sets   set 0-4: the five sets chosen in OTO-ESC_fix.ipynb; set 5-2004: Halton sequence (bases 2, 3, 5)
%            with k log-uniform in [1e-3, 5], a in [0.005, 0.6], f in [0.5, 10] Hz
% Plants     600 in seven families: static (41), exp (72), timescale (30), linear (30), step (36),
%            sine (27), random (364, as in OTO-ESC_fix, MATLAB's default random stream)
% Blocks     static, exp1, exp2, timescale, linear, step, sine, random1 ... random6 (steady start at 0.5),
%            from0.3, from0.7 (30 plants, plasma and r_hat start at 0.3 / 0.7),
%            dt0.002 (the five chosen and the first 200 quasi-random sets on 50 plants, dt = 0.002 s)
% Output     data/OTO-crossed/OTO-crossed-{sets,plants,references}-matlab.csv and
%            OTO-crossed-<block>-matlab.csv with the columns set, plant, energy_gain (= energy_ESC -
%            energy_const), converged, convergence_time, settling_time_0.01, settling_time_0.02,
%            tracking_error, tracking_error_late, r_hat_final. The "-matlab" ending keeps the stored
%            Python files from being replaced.
%
% The simulation is in Tools/esc_sim.m. All blocks take about 2 hours in Python on one core; to use
% more cores, start several MATLAB sessions with different blocks_to_run.

clear; clc;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, '..', 'Tools'));

%% Batch sweep settings
blocks_to_run = 'all';      % 'all', or e.g. {'static', 'exp1'}
write_tables = true;        % write the sets, plants and references tables
set_rows = [];              % [] = all sets of the block, or positions, e.g. 1:100
plant_rows = [];            % [] = all plants of the block, or positions, e.g. 1:10
output_folder = esc_paths('OTO-crossed');   % data/OTO-crossed/
overwrite = false;          % true: replace existing output files

%% Simulation settings
tend = 100;                 % run length [s]
dt = 0.01;                  % time step [s] (the dt0.002 block uses dt_check)
dt_check = 0.002;
chunk = 10000;              % runs simulated at once (memory)

%% ESC sets
n_quasi_random = 2000;
n_dt_sets = 200;            % quasi-random sets in the dt0.002 block (the first ones of the Halton sequence)
k_range = [1e-3, 5];        % optimizer gain, log-uniform
a_range = [0.005, 0.6];     % dither amplitude
f_range = [0.5, 10];        % dither frequency [Hz]
chosen_names = {'reference', 'fastest', 'fastest a>=0.15', 'fastest f<=3', 'best energy a>=0.1'};
chosen_kaf = [1, 0.2, 6; 0.255, 0.0517, 8.41; 0.265, 0.192, 9.09; 0.0982, 0.0556, 2.97; 1.6, 0.11, 9.91];

log_range = log10(k_range);
set_k = [chosen_kaf(:, 1); 10 .^ (log_range(1) + diff(log_range) * halton(n_quasi_random, 2))];
set_a = [chosen_kaf(:, 2); a_range(1) + diff(a_range) * halton(n_quasi_random, 3)];
set_f = [chosen_kaf(:, 3); f_range(1) + diff(f_range) * halton(n_quasi_random, 5)];
set_name = [chosen_names'; repmat({''}, n_quasi_random, 1)];
n_sets = numel(set_k);
set_id = (0:n_sets - 1)';

%% Plants (thousandths of r are used where both languages must give exactly the same numbers)
n_random_plants = 364;
random_r_ideal_0_range = [0.45, 0.55];
random_lambda_range = [-0.002, 0.002];   % [1/s]
random_seed = 0;
off_starts = [0.3, 0.7];
OFF_START_STATIC = [420, 460, 500, 540, 580];
EXP_SUBSET = [460 540; 540 460; 480 420; 520 580; 460 500; 420 580; 580 420; 500 560; 500 440; 440 480];
DT_STATIC = [400, 450, 475, 500, 525, 550, 600];
TIMESCALE_STATIC = [450, 475, 500, 525, 550];
TIMESCALE_EXP = [460 540; 540 460; 480 420; 520 580; 460 500];
TIMESCALES = [0.5, 2, 3];
SHAPE_NAMES = {'exp', 'linear', 'step', 'sine'};

P = struct('family', {{}}, 'r0', [], 'lam', [], 'shape', [], 'size', [], 'tdrift', [], 'scale', [], ...
           'start', [], 'finish', []);
for j = 0:40
    P = add_plant(P, 'static', (400 + 5 * j) / 1000, 0, 0, 0, tend, 1, 400 + 5 * j, 400 + 5 * j);
end
for s = 0:8
    for e = 0:8
        if s ~= e
            r_start = 420 + 20 * s; r_end = 420 + 20 * e;
            P = add_plant(P, 'exp', r_start / 1000, log((r_end / 1000) / (r_start / 1000)) / tend, 0, 0, tend, 1, r_start, r_end);
        end
    end
end
for scale = TIMESCALES
    for r = TIMESCALE_STATIC
        P = add_plant(P, 'timescale', r / 1000, 0, 0, 0, tend, scale, r, r);
    end
    for q = 1:size(TIMESCALE_EXP, 1)
        r_start = TIMESCALE_EXP(q, 1); r_end = TIMESCALE_EXP(q, 2);
        P = add_plant(P, 'timescale', r_start / 1000, log((r_end / 1000) / (r_start / 1000)) / tend, 0, 0, tend, scale, r_start, r_end);
    end
end
for r = [440, 470, 500, 530, 560]
    for d = [-80, -50, -20, 20, 50, 80]
        P = add_plant(P, 'linear', r / 1000, 0, 1, d / 1000, tend, 1, -1, -1);
    end
end
for r = [460, 500, 540]
    for d = [-60, -30, 30, 60]
        for t_step = [20, 50, 80]
            P = add_plant(P, 'step', r / 1000, 0, 2, d / 1000, t_step, 1, -1, -1);
        end
    end
end
for r = [460, 500, 540]
    for amplitude = [10, 30, 60]
        for period = [10, 30, 100]
            P = add_plant(P, 'sine', r / 1000, 0, 3, amplitude / 1000, period, 1, -1, -1);
        end
    end
end
esc_rng(random_seed, 0);
u = esc_draw(n_random_plants, 2);     % one trial draws r_ideal_0, then lambda
r0_random = random_r_ideal_0_range(1) + diff(random_r_ideal_0_range) * u(:, 1);
lam_random = random_lambda_range(1) + diff(random_lambda_range) * u(:, 2);
for j = 1:n_random_plants
    P = add_plant(P, 'random', r0_random(j), lam_random(j), 0, 0, tend, 1, -1, -1);
end
n_plants = numel(P.r0);
plant_id = (0:n_plants - 1)';

% r_ideal over the run, sampled every dt: end value, mean, rms distance from 0.5, drift class
t_grid = (0:round(tend / dt))' * dt;
path = r_ideal_path(t_grid, P);
r_ideal_end = path(end, :)';
r_ideal_mean = mean(path, 1)';
offset_rms = sqrt(mean((path - 0.5) .^ 2, 1))';
d0 = P.r0 - 0.5; d1 = r_ideal_end - 0.5;
moving = (P.lam ~= 0) | (P.size ~= 0);
drift_class = repmat({'towards'}, n_plants, 1);
drift_class(abs(d1) > abs(d0)) = {'away'};
drift_class(d0 .* d1 < 0) = {'through'};
drift_class(P.shape == 3) = {'oscillating'};
drift_class(~moving) = {'static'};

% blocks of the steady start (at most 61 plants per block)
block = P.family;
exp_ids = find(strcmp(P.family, 'exp'));
block(exp_ids(1:36)) = {'exp1'}; block(exp_ids(37:end)) = {'exp2'};
random_ids = find(strcmp(P.family, 'random'));
n_part = 6; base = floor(numel(random_ids) / n_part); extra = mod(numel(random_ids), n_part);
first = 1;
for j = 1:n_part
    len = base + (j <= extra);
    block(random_ids(first:first + len - 1)) = {sprintf('random%d', j)};
    first = first + len;
end

% plants of the off-0.5 starts and of the time-step check
off_start = false(n_plants, 1);
for r = OFF_START_STATIC, off_start(find_plant(P, 'static', r, r, 1)) = true; end
for scale = TIMESCALES, for r = TIMESCALE_STATIC, off_start(find_plant(P, 'timescale', r, r, scale)) = true; end, end
for q = 1:size(EXP_SUBSET, 1), off_start(find_plant(P, 'exp', EXP_SUBSET(q, 1), EXP_SUBSET(q, 2), 1)) = true; end
dt_plant = false(n_plants, 1);
for r = DT_STATIC, dt_plant(find_plant(P, 'static', r, r, 1)) = true; end
for q = 1:8, dt_plant(find_plant(P, 'exp', EXP_SUBSET(q, 1), EXP_SUBSET(q, 2), 1)) = true; end
for scale = TIMESCALES, for r = [450, 550], dt_plant(find_plant(P, 'timescale', r, r, scale)) = true; end, end
families = {'linear', 'step', 'sine', 'random'}; counts = [6, 6, 6, 11];
for q = 1:numel(families)
    ids = find(strcmp(P.family, families{q})); n = numel(ids); m = counts(q);
    dt_plant(ids(floor((0:m - 1) * (n - 1) / (m - 1)) + 1)) = true;
end

% list of blocks: name, plant positions (1-based), set positions (1-based), start ratio, time step
B = struct('name', {}, 'plants', {}, 'sets', {}, 'start', {}, 'dt', {});
names = [{'static', 'exp1', 'exp2', 'timescale', 'linear', 'step', 'sine'}, arrayfun(@(j) sprintf('random%d', j), 1:6, 'UniformOutput', false)];
for j = 1:numel(names)
    B(end + 1) = struct('name', names{j}, 'plants', find(strcmp(block, names{j})), 'sets', (1:n_sets)', 'start', 0.5, 'dt', dt); %#ok<SAGROW>
end
for start = off_starts
    B(end + 1) = struct('name', sprintf('from%g', start), 'plants', find(off_start), 'sets', (1:n_sets)', 'start', start, 'dt', dt); %#ok<SAGROW>
end
% the first points of a Halton sequence are spread evenly; every tenth point would not be (10 is a multiple of the bases)
dt_sets = [(1:size(chosen_kaf, 1))'; size(chosen_kaf, 1) + (1:n_dt_sets)'];
B(end + 1) = struct('name', 'dt0.002', 'plants', find(dt_plant), 'sets', dt_sets, 'start', 0.5, 'dt', dt_check);

%% Tables
if write_tables
    file = checked(fullfile(output_folder, 'OTO-crossed-sets-matlab.csv'), overwrite);
    fid = fopen(file, 'w');
    fprintf(fid, 'set,optimizer_gain,dither_amplitude,dither_frequency,chosen\n');
    for j = 1:n_sets
        % (the name is joined first: fprintf stops at a %s whose argument is empty)
        fprintf(fid, '%s\n', [sprintf('%d,%.15g,%.15g,%.15g,', set_id(j), set_k(j), set_a(j), set_f(j)), set_name{j}]);
    end
    fclose(fid);
    fprintf('%d rows written to %s\n', n_sets, file);

    file = checked(fullfile(output_folder, 'OTO-crossed-plants-matlab.csv'), overwrite);
    fid = fopen(file, 'w');
    fprintf(fid, ['plant,family,block,drift_shape,r_ideal_0,lambda_r_ideal,drift_size,drift_time,tau_scale,', ...
                  'r_ideal_end,r_ideal_mean,offset_rms,drift_class,off_start,dt_check\n']);
    for j = 1:n_plants
        fprintf(fid, '%d,%s,%s,%s,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%.15g,%s,%d,%d\n', plant_id(j), ...
                P.family{j}, block{j}, SHAPE_NAMES{P.shape(j) + 1}, P.r0(j), P.lam(j), P.size(j), P.tdrift(j), ...
                P.scale(j), r_ideal_end(j), r_ideal_mean(j), offset_rms(j), drift_class{j}, double(off_start(j)), double(dt_plant(j)));
    end
    fclose(fid);
    fprintf('%d rows written to %s\n', n_plants, file);

    file = checked(fullfile(output_folder, 'OTO-crossed-references-matlab.csv'), overwrite);
    fid = fopen(file, 'w');
    fprintf(fid, 'block,plant,energy_const,energy_ideal\n');
    for q = 1:numel(B)
        [e_const, e_ideal] = references(P, B(q).plants, B(q).start, B(q).dt, tend);
        for j = 1:numel(B(q).plants)
            fprintf(fid, '%s,%d,%.15g,%.15g\n', B(q).name, plant_id(B(q).plants(j)), e_const(j), e_ideal(j));
        end
    end
    fclose(fid);
    fprintf('references written to %s\n', file);
end

%% Blocks
if ischar(blocks_to_run) && strcmp(blocks_to_run, 'all')
    blocks_to_run = {B.name};
end
for q = find(ismember({B.name}, blocks_to_run))
    plants_here = B(q).plants; sets_here = B(q).sets;
    suffix = '';
    if ~isempty(plant_rows), plants_here = plants_here(plant_rows); suffix = [suffix, sprintf('-plants%d-%d', plant_rows(1), plant_rows(end))]; end
    if ~isempty(set_rows), sets_here = sets_here(set_rows); suffix = [suffix, sprintf('-sets%d-%d', set_rows(1), set_rows(end))]; end
    file = checked(fullfile(output_folder, sprintf('OTO-crossed-%s%s-matlab.csv', B(q).name, suffix)), overwrite);
    n_p = numel(plants_here); n_s = numel(sets_here);

    % all sets on all plants; rows ordered plant by plant, sets inside
    rep = @(x) repelem(x(plants_here), n_s, 1);
    esc = esc_sim(repmat(set_k(sets_here), n_p, 1), repmat(set_a(sets_here), n_p, 1), repmat(set_f(sets_here), n_p, 1), ...
                  'RIdeal0', rep(P.r0), 'LambdaRIdeal', rep(P.lam), 'DriftShape', rep(P.shape), ...
                  'DriftSize', rep(P.size), 'DriftTime', rep(P.tdrift), 'TauScale', rep(P.scale), ...
                  'RHat0', B(q).start, 'SteadyStart', B(q).start, 'Track', true, 'SettleTolerances', [0.01 0.02], ...
                  'Dt', B(q).dt, 'Tend', tend, 'Chunk', chunk, 'Progress', B(q).name);
    e_const = references(P, plants_here, B(q).start, B(q).dt, tend);

    rows = [repmat(set_id(sets_here), n_p, 1), repelem(plant_id(plants_here), n_s, 1), esc.energy - repelem(e_const, n_s, 1), ...
            double(esc.converged), esc.convergence_time, esc.settling_time(:, 1), esc.settling_time(:, 2), ...
            esc.tracking_error, esc.tracking_error_late, esc.r_hat_final];
    fid = fopen(file, 'w');
    fprintf(fid, ['set,plant,energy_gain,converged,convergence_time,settling_time_0.01,settling_time_0.02,', ...
                  'tracking_error,tracking_error_late,r_hat_final\n']);
    fprintf(fid, '%d,%d,%.9g,%d,%.6g,%.6g,%.6g,%.6g,%.6g,%.9g\n', rows.');
    fclose(fid);
    fprintf('%s: %d rows written to %s, ESC wins %.3f, converged %.3f\n', B(q).name, size(rows, 1), file, ...
            mean(rows(:, 3) > 0), mean(rows(:, 4)));
end


%% Local functions
function P = add_plant(P, family, r0, lam, shape, drift_size, t_drift, scale, start, finish)
P.family{end + 1, 1} = family;
P.r0(end + 1, 1) = r0; P.lam(end + 1, 1) = lam; P.shape(end + 1, 1) = shape;
P.size(end + 1, 1) = drift_size; P.tdrift(end + 1, 1) = t_drift; P.scale(end + 1, 1) = scale;
P.start(end + 1, 1) = start; P.finish(end + 1, 1) = finish;
end

function path = r_ideal_path(t, P)
% r_ideal(t) of every plant (time x plants), the same formula as in esc_sim
path = P.r0' .* exp(P.lam' .* t);
g = zeros(size(path));
c = P.shape' == 1; g(:, c) = t ./ P.tdrift(c)';
c = P.shape' == 2; g(:, c) = double(t >= P.tdrift(c)');
c = P.shape' == 3; g(:, c) = sin(2 * pi * t ./ P.tdrift(c)');
path = path + P.size' .* g;
end

function id = find_plant(P, family, start, finish, scale)
% position of a static or exponential plant given in thousandths
id = find(strcmp(P.family, family) & P.start == start & P.finish == finish & P.scale == scale);
assert(numel(id) == 1, 'plant %s %d-%d x%g not found once', family, start, finish, scale);
end

function [e_const, e_ideal] = references(P, ids, start, step, tend)
% energy with the ratio fixed at 0.5 and with the ratio following r_ideal(t), from the same start
plant = {'RIdeal0', P.r0(ids), 'LambdaRIdeal', P.lam(ids), 'DriftShape', P.shape(ids), 'DriftSize', P.size(ids), ...
         'DriftTime', P.tdrift(ids), 'TauScale', P.scale(ids), 'SteadyStart', start, 'Dt', step, 'Tend', tend};
fixed = esc_sim(0, 0, 1, 'UseESC', false, 'FixedRatio', 0.5, plant{:});
e_const = fixed.energy;
if nargout > 1
    ideal = esc_sim(0, 0, 1, 'UseESC', false, 'FixedRatio', 'ideal', plant{:});
    e_ideal = ideal.energy;
end
end

function v = halton(n, base)
% points 1..n of the van der Corput sequence in `base` (one coordinate of the Halton sequence)
i = (1:n)';
scale = ones(n, 1);
v = zeros(n, 1);
while any(i > 0)
    scale = scale / base;
    v = v + scale .* mod(i, base);
    i = floor(i / base);
end
end

function file = checked(file, overwrite)
if isfile(file) && ~overwrite
    error('%s exists already. Set overwrite = true to replace it.', file);
end
end
